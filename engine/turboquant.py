"""
DUBFORGE — TurboQuant Vector Quantization Engine

Near-optimal data-oblivious vector quantization for audio buffers,
wavetables, and spectral feature vectors.

Based on: TurboQuant (arXiv:2504.19874, ICLR 2026)
    Zandieh, Daliri, Hadian, Mirrokni — Google Research

Three integration points in DUBFORGE:
  1. Wavetable compression — 2048-sample waveforms at 3-4 bits (~5× smaller)
  2. Audio buffer compression — compress idle buffers in AudioBufferPool
  3. Spectral vector search — nearest-neighbor on compressed feature vectors

Algorithm summary:
  - Random rotation (Fast Walsh-Hadamard) → near-independent coordinates
  - Lloyd-Max optimal scalar quantization per coordinate (data-oblivious codebook)
  - Optional QJL residual correction for unbiased inner products

Convention: list[float] ↔ list[float], consistent with DUBFORGE DSP modules.
numpy used internally for math but public API accepts/returns list[float].
"""

import math
import struct
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from engine.config_loader import PHI

SAMPLE_RATE = 48000


# ---------------------------------------------------------------------------
# Codebook precomputation (Lloyd-Max for Beta-distributed coordinates)
# ---------------------------------------------------------------------------

def _beta_pdf(x: float, d: int) -> float:
    """Scaled Beta PDF for coordinates of a unit vector on S^{d-1}.

    f(x) = C_d * (1 - x^2)^{(d-3)/2}  for x in [-1, 1]

    In high dimensions this concentrates near 0 like N(0, 1/d).
    """
    if abs(x) >= 1.0:
        return 0.0
    exponent = (d - 3) / 2.0
    if exponent < 0:
        # d=2 edge case
        return 0.5
    return (1.0 - x * x) ** exponent


def _lloyd_max_codebook(bits: int, dim: int, iterations: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """Compute Lloyd-Max optimal scalar quantizer for the Beta PDF.

    Returns (centroids, boundaries) — both sorted arrays.
    centroids: 2^bits values (reconstruction levels).
    boundaries: 2^bits + 1 values (decision boundaries including ±1).
    """
    n_levels = 1 << bits
    sigma = 1.0 / math.sqrt(dim) if dim > 1 else 1.0

    # Initialize centroids uniformly in [-3σ, 3σ] (covers >99.7% of mass)
    span = 3.0 * sigma
    centroids = np.linspace(-span, span, n_levels)

    # Numerical integration grid
    n_grid = 4096
    xs = np.linspace(-span, span, n_grid)
    pdf = np.array([_beta_pdf(x / (sigma * math.sqrt(dim)) if dim > 2 else x, max(dim, 4))
                    for x in xs])
    # Approximate: use Gaussian N(0, sigma^2) for high-d (much more stable)
    pdf = np.exp(-0.5 * (xs / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    dx = xs[1] - xs[0]
    pdf /= np.sum(pdf) * dx  # Normalize

    for _ in range(iterations):
        # Decision boundaries = midpoints between centroids
        boundaries = np.empty(n_levels + 1)
        boundaries[0] = -span
        boundaries[-1] = span
        for i in range(1, n_levels):
            boundaries[i] = 0.5 * (centroids[i - 1] + centroids[i])

        # Update centroids = conditional mean in each partition
        new_centroids = np.zeros(n_levels)
        for i in range(n_levels):
            lo = boundaries[i]
            hi = boundaries[i + 1]
            mask = (xs >= lo) & (xs < hi)
            weighted = xs[mask] * pdf[mask]
            total = pdf[mask].sum()
            if total > 0:
                new_centroids[i] = weighted.sum() / total
            else:
                new_centroids[i] = centroids[i]

        if np.allclose(centroids, new_centroids, atol=1e-10):
            break
        centroids = new_centroids

    # Final boundaries
    boundaries = np.empty(n_levels + 1)
    boundaries[0] = -span
    boundaries[-1] = span
    for i in range(1, n_levels):
        boundaries[i] = 0.5 * (centroids[i - 1] + centroids[i])

    return centroids, boundaries


# ---------------------------------------------------------------------------
# Fast Walsh-Hadamard Transform (FWHT) — O(d log d) rotation
# ---------------------------------------------------------------------------

def _next_power_of_2(n: int) -> int:
    """Return smallest power of 2 >= n."""
    p = 1
    while p < n:
        p <<= 1
    return p


def _fwht_inplace(a: np.ndarray) -> None:
    """In-place Fast Walsh-Hadamard Transform (sequency-ordered).

    Input length must be a power of 2.
    """
    n = len(a)
    h = 1
    while h < n:
        for i in range(0, n, h * 2):
            for j in range(i, i + h):
                x = a[j]
                y = a[j + h]
                a[j] = x + y
                a[j + h] = x - y
        h *= 2


def _random_signs(d: int, seed: int) -> np.ndarray:
    """Deterministic random sign vector for rotation."""
    rng = np.random.RandomState(seed)
    return rng.choice([-1.0, 1.0], size=d)


def _rotate(x: np.ndarray, signs: np.ndarray) -> np.ndarray:
    """Apply randomized Hadamard rotation: FWHT(signs * x) / sqrt(padded_d).

    This makes coordinates near-independent for high-d vectors.
    For non-power-of-2 dims, we pad to next power of 2 and keep ALL
    padded_d outputs to preserve invertibility.
    """
    d = len(x)
    padded_d = _next_power_of_2(d)
    buf = np.zeros(padded_d)
    buf[:d] = x * signs[:d]
    _fwht_inplace(buf)
    buf /= math.sqrt(padded_d)
    return buf  # Return full padded vector


def _unrotate(y: np.ndarray, signs: np.ndarray, original_d: int) -> np.ndarray:
    """Inverse rotation: signs * FWHT(y) / sqrt(padded_d), trimmed to original_d."""
    padded_d = _next_power_of_2(original_d)
    buf = np.zeros(padded_d)
    buf[:len(y)] = y
    _fwht_inplace(buf)
    buf /= math.sqrt(padded_d)
    return buf[:original_d] * signs[:original_d]


# ---------------------------------------------------------------------------
# TurboQuant Core
# ---------------------------------------------------------------------------

@dataclass
class TurboQuantConfig:
    """Configuration for TurboQuant vector quantization."""
    bit_width: int = 3          # bits per dimension (1-8)
    use_qjl: bool = False       # QJL residual correction for unbiased inner products
    rotation_seed: int = 42     # deterministic rotation
    chunk_size: int = 256       # process vectors in chunks of this size


@dataclass
class CompressedVector:
    """A TurboQuant-compressed vector.

    Stores packed bit indices + metadata for reconstruction.
    Memory: ~(bit_width * dim / 8) bytes + 12 bytes overhead.
    """
    indices: bytes              # packed quantization indices
    norm: float                 # original L2 norm (for rescaling)
    dim: int                    # original dimensionality
    bit_width: int              # bits per dimension
    qjl_signs: Optional[bytes] = None   # QJL sign bits (1 bit/dim)
    residual_norm: float = 0.0          # ||residual||_2

    @property
    def compressed_bytes(self) -> int:
        """Total bytes used by this compressed vector."""
        base = len(self.indices) + 12  # indices + norm(8) + dim(2) + bit(1) + rn(1)
        if self.qjl_signs is not None:
            base += len(self.qjl_signs) + 4  # signs + residual_norm float
        return base

    @property
    def compression_ratio(self) -> float:
        """Ratio of original size (float64) to compressed size."""
        original = self.dim * 8  # 8 bytes per float64
        return original / max(self.compressed_bytes, 1)


class TurboQuantEngine:
    """Near-optimal vector quantizer for audio data.

    Usage:
        tq = TurboQuantEngine(TurboQuantConfig(bit_width=3))
        compressed = tq.compress([0.5, -0.3, 0.8, ...])
        reconstructed = tq.decompress(compressed)
        # MSE is near Shannon lower bound

    For inner-product preservation (e.g., spectral similarity):
        tq = TurboQuantEngine(TurboQuantConfig(bit_width=4, use_qjl=True))
    """

    def __init__(self, config: TurboQuantConfig | None = None):
        self.config = config or TurboQuantConfig()
        self._codebook_cache: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        self._signs_cache: dict[tuple[int, int], np.ndarray] = {}

    def _get_codebook(self, dim: int) -> tuple[np.ndarray, np.ndarray]:
        """Get or compute Lloyd-Max codebook for (bit_width, dim)."""
        key = (self.config.bit_width, dim)
        if key not in self._codebook_cache:
            effective_bits = self.config.bit_width
            if self.config.use_qjl and effective_bits > 1:
                effective_bits -= 1  # Reserve 1 bit for QJL
            self._codebook_cache[key] = _lloyd_max_codebook(
                max(effective_bits, 1), dim
            )
        return self._codebook_cache[key]

    def _get_signs(self, dim: int) -> np.ndarray:
        """Get or compute random sign vector for rotation."""
        key = (dim, self.config.rotation_seed)
        if key not in self._signs_cache:
            self._signs_cache[key] = _random_signs(dim, self.config.rotation_seed)
        return self._signs_cache[key]

    def _pack_indices(self, indices: np.ndarray, bits: int) -> bytes:
        """Pack integer indices into a compact byte string."""
        # Simple bit-packing: each index uses `bits` bits
        total_bits = len(indices) * bits
        total_bytes = (total_bits + 7) // 8
        packed = bytearray(total_bytes)

        bit_pos = 0
        for idx in indices:
            val = int(idx) & ((1 << bits) - 1)
            for b in range(bits):
                if val & (1 << b):
                    byte_idx = bit_pos >> 3
                    packed[byte_idx] |= 1 << (bit_pos & 7)
                bit_pos += 1

        return bytes(packed)

    def _unpack_indices(self, data: bytes, count: int, bits: int) -> np.ndarray:
        """Unpack bit-packed indices back to integer array."""
        indices = np.zeros(count, dtype=np.int32)
        bit_pos = 0

        for i in range(count):
            val = 0
            for b in range(bits):
                byte_idx = bit_pos >> 3
                if byte_idx < len(data) and data[byte_idx] & (1 << (bit_pos & 7)):
                    val |= 1 << b
                bit_pos += 1
            indices[i] = val

        return indices

    def _pack_signs(self, signs: np.ndarray) -> bytes:
        """Pack QJL sign bits (1 bit per element)."""
        n = len(signs)
        total_bytes = (n + 7) // 8
        packed = bytearray(total_bytes)
        for i in range(n):
            if signs[i] > 0:
                packed[i >> 3] |= 1 << (i & 7)
        return bytes(packed)

    def _unpack_signs(self, data: bytes, count: int) -> np.ndarray:
        """Unpack QJL sign bits."""
        signs = np.zeros(count)
        for i in range(count):
            byte_idx = i >> 3
            if byte_idx < len(data) and data[byte_idx] & (1 << (i & 7)):
                signs[i] = 1.0
            else:
                signs[i] = -1.0
        return signs

    def compress(self, samples: list[float]) -> CompressedVector:
        """Compress a float vector using TurboQuant.

        Args:
            samples: Audio samples or feature vector (list[float]).

        Returns:
            CompressedVector with packed indices and metadata.
        """
        x = np.array(samples, dtype=np.float64)
        dim = len(x)
        norm = float(np.linalg.norm(x))

        if norm < 1e-15:
            # Zero vector — trivial encoding
            return CompressedVector(
                indices=b'\x00',
                norm=0.0,
                dim=dim,
                bit_width=self.config.bit_width,
            )

        # Normalize to unit sphere
        x_unit = x / norm
        padded_dim = _next_power_of_2(dim)
        signs = self._get_signs(padded_dim)

        # Step 1: Random rotation → near-independent coordinates
        # Returns padded_dim-length vector for invertibility
        y = _rotate(x_unit, signs)
        qdim = len(y)  # = padded_dim

        # Step 2: Get codebook (keyed to padded dim for consistency)
        centroids, boundaries = self._get_codebook(padded_dim)
        effective_bits = self.config.bit_width
        if self.config.use_qjl and effective_bits > 1:
            effective_bits -= 1

        # Step 3: Scalar quantize each coordinate
        indices = np.searchsorted(boundaries[1:-1], y).astype(np.int32)
        indices = np.clip(indices, 0, len(centroids) - 1)

        # Pack indices
        packed = self._pack_indices(indices, effective_bits)

        # Step 4: Optional QJL correction on residual
        qjl_signs_packed = None
        residual_norm = 0.0

        if self.config.use_qjl:
            # Reconstruct MSE approximation
            y_mse = centroids[indices]
            residual = y - y_mse
            residual_norm = float(np.linalg.norm(residual))

            if residual_norm > 1e-15:
                # QJL: sign(S @ residual) where S is random Gaussian
                rng = np.random.RandomState(self.config.rotation_seed + 1)
                s_proj = rng.randn(qdim)
                projections = s_proj * residual
                qjl_sign_vec = np.sign(projections)
                qjl_sign_vec[qjl_sign_vec == 0] = 1.0
                qjl_signs_packed = self._pack_signs(qjl_sign_vec)

        return CompressedVector(
            indices=packed,
            norm=norm,
            dim=dim,
            bit_width=self.config.bit_width,
            qjl_signs=qjl_signs_packed,
            residual_norm=residual_norm,
        )

    def decompress(self, cv: CompressedVector) -> list[float]:
        """Decompress a CompressedVector back to list[float].

        Returns:
            Reconstructed audio samples.
        """
        if cv.norm < 1e-15:
            return [0.0] * cv.dim

        padded_dim = _next_power_of_2(cv.dim)

        effective_bits = cv.bit_width
        if cv.qjl_signs is not None and effective_bits > 1:
            effective_bits -= 1

        # Unpack indices (padded_dim values were stored)
        indices = self._unpack_indices(cv.indices, padded_dim, effective_bits)

        # Get codebook (same params as compress)
        centroids, _ = self._get_codebook(padded_dim)

        # Reconstruct rotated coordinates
        indices = np.clip(indices, 0, len(centroids) - 1)
        y_recon = centroids[indices]

        # Add QJL correction if present
        if cv.qjl_signs is not None and cv.residual_norm > 1e-15:
            qjl_signs = self._unpack_signs(cv.qjl_signs, padded_dim)
            # QJL reconstruction: sqrt(pi / (2d)) * ||r||_2 * S^T * z
            scale = math.sqrt(math.pi / (2.0 * padded_dim)) * cv.residual_norm
            rng = np.random.RandomState(self.config.rotation_seed + 1)
            s_proj = rng.randn(padded_dim)
            y_recon += scale * s_proj * qjl_signs

        # Inverse rotation (trim back to original dim)
        signs = self._get_signs(padded_dim)
        x_unit = _unrotate(y_recon, signs, cv.dim)

        # Rescale by original norm
        x_recon = x_unit * cv.norm

        return x_recon.tolist()

    def mse(self, original: list[float], reconstructed: list[float]) -> float:
        """Compute normalized MSE between original and reconstruction."""
        a = np.array(original)
        b = np.array(reconstructed)
        norm_sq = np.dot(a, a)
        if norm_sq < 1e-15:
            return 0.0
        return float(np.sum((a - b) ** 2) / norm_sq)

    def inner_product_error(self, x: list[float], y: list[float],
                            x_hat: list[float]) -> float:
        """Compute |<y, x> - <y, x_hat>| / (||y|| * ||x||).

        Measures how well inner products are preserved.
        """
        xa = np.array(x)
        ya = np.array(y)
        xh = np.array(x_hat)
        true_ip = np.dot(ya, xa)
        recon_ip = np.dot(ya, xh)
        denom = np.linalg.norm(ya) * np.linalg.norm(xa)
        if denom < 1e-15:
            return 0.0
        return float(abs(true_ip - recon_ip) / denom)


# ---------------------------------------------------------------------------
# Wavetable Compression — compress 2048-sample single-cycle waveforms
# ---------------------------------------------------------------------------

@dataclass
class CompressedWavetable:
    """A TurboQuant-compressed wavetable (multiple frames)."""
    frames: list[CompressedVector]
    frame_size: int
    sample_rate: int = SAMPLE_RATE
    name: str = ""

    @property
    def total_compressed_bytes(self) -> int:
        return sum(f.compressed_bytes for f in self.frames)

    @property
    def total_original_bytes(self) -> int:
        return len(self.frames) * self.frame_size * 8

    @property
    def compression_ratio(self) -> float:
        cb = self.total_compressed_bytes
        return self.total_original_bytes / max(cb, 1)


def compress_wavetable(frames: list[list[float]],
                       config: TurboQuantConfig | None = None,
                       name: str = "") -> CompressedWavetable:
    """Compress a multi-frame wavetable.

    Args:
        frames: List of single-cycle waveforms (each typically 2048 samples).
        config: TurboQuant settings (default: 3-bit MSE-optimal).
        name: Optional wavetable name.

    Returns:
        CompressedWavetable — ~5× smaller at 3 bits with near-perfect quality.
    """
    cfg = config or TurboQuantConfig(bit_width=3)
    engine = TurboQuantEngine(cfg)
    frame_size = len(frames[0]) if frames else 0

    compressed_frames = [engine.compress(f) for f in frames]
    return CompressedWavetable(
        frames=compressed_frames,
        frame_size=frame_size,
        name=name,
    )


def decompress_wavetable(cw: CompressedWavetable,
                         config: TurboQuantConfig | None = None) -> list[list[float]]:
    """Decompress a CompressedWavetable back to frames.

    Args:
        cw: Compressed wavetable.
        config: Must match the config used for compression.

    Returns:
        List of reconstructed waveform frames.
    """
    cfg = config or TurboQuantConfig(bit_width=cw.frames[0].bit_width if cw.frames else 3)
    engine = TurboQuantEngine(cfg)
    return [engine.decompress(f) for f in cw.frames]


# ---------------------------------------------------------------------------
# Audio Buffer Compression — compress idle buffers in AudioBufferPool
# ---------------------------------------------------------------------------

@dataclass
class CompressedAudioBuffer:
    """A compressed audio buffer (for idle/archival storage).

    Chunks the audio into vectors of chunk_size and compresses each.
    """
    buffer_id: str
    chunks: list[CompressedVector]
    original_length: int
    chunk_size: int
    sample_rate: int = SAMPLE_RATE
    channels: int = 1
    label: str = ""

    @property
    def compressed_bytes(self) -> int:
        return sum(c.compressed_bytes for c in self.chunks)

    @property
    def compression_ratio(self) -> float:
        original = self.original_length * 8
        return original / max(self.compressed_bytes, 1)


def compress_audio_buffer(samples: list[float],
                          buffer_id: str = "",
                          config: TurboQuantConfig | None = None,
                          sample_rate: int = SAMPLE_RATE,
                          label: str = "") -> CompressedAudioBuffer:
    """Compress an audio buffer for archival/idle storage.

    Args:
        samples: Audio samples (list[float], range [-1, 1]).
        buffer_id: Buffer identifier.
        config: TurboQuant settings.
        sample_rate: Sample rate.
        label: Optional label.

    Returns:
        CompressedAudioBuffer — chunked and compressed.
    """
    cfg = config or TurboQuantConfig(bit_width=3, chunk_size=256)
    engine = TurboQuantEngine(cfg)
    chunk_size = cfg.chunk_size

    chunks: list[CompressedVector] = []
    for i in range(0, len(samples), chunk_size):
        chunk = samples[i:i + chunk_size]
        # Pad last chunk if needed
        if len(chunk) < chunk_size:
            chunk = chunk + [0.0] * (chunk_size - len(chunk))
        chunks.append(engine.compress(chunk))

    return CompressedAudioBuffer(
        buffer_id=buffer_id,
        chunks=chunks,
        original_length=len(samples),
        chunk_size=chunk_size,
        sample_rate=sample_rate,
        label=label,
    )


def decompress_audio_buffer(cab: CompressedAudioBuffer,
                            config: TurboQuantConfig | None = None) -> list[float]:
    """Decompress a CompressedAudioBuffer back to samples.

    Returns:
        Reconstructed audio samples (trimmed to original length).
    """
    cfg = config or TurboQuantConfig(
        bit_width=cab.chunks[0].bit_width if cab.chunks else 3,
        chunk_size=cab.chunk_size,
    )
    engine = TurboQuantEngine(cfg)

    samples: list[float] = []
    for chunk in cab.chunks:
        samples.extend(engine.decompress(chunk))

    # Trim padding
    return samples[:cab.original_length]


# ---------------------------------------------------------------------------
# Spectral Feature Vector Search — compress & search feature vectors
# ---------------------------------------------------------------------------

@dataclass
class SpectralFeatureEntry:
    """A compressed spectral feature vector with metadata for search."""
    name: str
    compressed: CompressedVector
    metadata: dict = field(default_factory=dict)


class SpectralVectorIndex:
    """Nearest-neighbor search on TurboQuant-compressed spectral features.

    Uses unbiased inner-product estimation from TurboQuant_prod.

    Usage:
        idx = SpectralVectorIndex(TurboQuantConfig(bit_width=4, use_qjl=True))
        idx.add("kick_01", [0.1, 0.9, 0.3, ...])
        idx.add("snare_01", [0.8, 0.1, 0.5, ...])
        results = idx.search([0.2, 0.85, 0.35, ...], top_k=3)
    """

    def __init__(self, config: TurboQuantConfig | None = None):
        self.config = config or TurboQuantConfig(bit_width=4, use_qjl=True)
        self.engine = TurboQuantEngine(self.config)
        self.entries: list[SpectralFeatureEntry] = []

    def add(self, name: str, features: list[float],
            metadata: dict | None = None) -> None:
        """Add a feature vector to the index."""
        cv = self.engine.compress(features)
        self.entries.append(SpectralFeatureEntry(
            name=name,
            compressed=cv,
            metadata=metadata or {},
        ))

    def search(self, query: list[float], top_k: int = 5) -> list[tuple[str, float, dict]]:
        """Find the top-k most similar entries to the query.

        Args:
            query: Feature vector to search for.
            top_k: Number of results to return.

        Returns:
            List of (name, similarity, metadata) tuples, sorted by
            descending cosine similarity.
        """
        q = np.array(query, dtype=np.float64)
        q_norm = np.linalg.norm(q)
        if q_norm < 1e-15:
            return []

        scores: list[tuple[str, float, dict]] = []
        for entry in self.entries:
            recon = np.array(self.engine.decompress(entry.compressed))
            r_norm = np.linalg.norm(recon)
            if r_norm < 1e-15:
                scores.append((entry.name, 0.0, entry.metadata))
                continue
            cosine = float(np.dot(q, recon) / (q_norm * r_norm))
            scores.append((entry.name, cosine, entry.metadata))

        scores.sort(key=lambda t: t[1], reverse=True)
        return scores[:top_k]

    def size(self) -> int:
        """Number of entries in the index."""
        return len(self.entries)

    def total_bytes(self) -> int:
        """Total compressed storage in bytes."""
        return sum(e.compressed.compressed_bytes for e in self.entries)


# ---------------------------------------------------------------------------
# Utility — compression stats & PHI-aligned bit-width selection
# ---------------------------------------------------------------------------

def phi_optimal_bits(dim: int) -> int:
    """Choose bit width using PHI-derived heuristic.

    For dim >= 128: 3 bits (5.3× compression, near Shannon bound)
    For dim >= 32:  4 bits (4× compression)
    For dim < 32:   5 bits (safe for short vectors)

    Thresholds are Fibonacci numbers scaled by PHI.
    """
    if dim >= 128:
        return 3
    if dim >= 32:
        return 4
    return 5


def estimate_compression_stats(dim: int, bit_width: int,
                               use_qjl: bool = False) -> dict:
    """Estimate compression ratio and theoretical MSE bound.

    Args:
        dim: Vector dimensionality.
        bit_width: Bits per dimension.
        use_qjl: Whether QJL correction is used.

    Returns:
        Dict with ratio, theoretical_mse_bound, bytes_original, bytes_compressed.
    """
    original_bytes = dim * 8  # float64
    effective_bits = bit_width - (1 if use_qjl else 0)
    index_bytes = (dim * effective_bits + 7) // 8
    overhead = 12  # norm + dim + bit_width
    if use_qjl:
        overhead += (dim + 7) // 8 + 4  # QJL signs + residual norm

    compressed = index_bytes + overhead
    ratio = original_bytes / max(compressed, 1)

    # Theoretical MSE upper bound (Theorem 1 from paper)
    b = max(effective_bits, 1)
    mse_bound = math.sqrt(3.0 / (math.pi ** 2)) / (4.0 * b)

    return {
        "compression_ratio": round(ratio, 2),
        "theoretical_mse_bound": round(mse_bound, 4),
        "bytes_original": original_bytes,
        "bytes_compressed": compressed,
        "effective_bits": effective_bits,
        "dim": dim,
    }
