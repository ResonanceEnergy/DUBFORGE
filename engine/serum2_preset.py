"""Serum 2 native .SerumPreset reader / writer / modifier.

Reads XferJson-wrapped presets (header + JSON metadata + zstd-compressed CBOR),
modifies parameters, re-serializes, and writes valid .SerumPreset files that
Serum 2 loads natively.

For ALS embedding, ``get_processor_state()`` and ``get_controller_state()``
return the real Serum 2 VST3 binary state bytes (captured via pedalboard from
the plugin's IComponent/IEditController).  These bytes are hex-encoded by
``als_generator`` and placed into ``<ProcessorState>``/``<ControllerState>``
so Ableton's VST3 host can call ``setState()`` successfully.
"""
from __future__ import annotations

import hashlib
import json
import logging
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cbor2
import zstandard

_log = logging.getLogger("dubforge.serum2_preset")

# ──────────────────────────────────────────────────────────────────────
# File format constants
# ──────────────────────────────────────────────────────────────────────
_MAGIC = b"XferJson\x00"              # 9-byte file header
_SERUM2_PRESET_DIR = Path(
    "/Library/Audio/Presets/Xfer Records/Serum 2 Presets"
)
_FACTORY_DIR = _SERUM2_PRESET_DIR / "Presets" / "Factory"
_USER_DIR = _SERUM2_PRESET_DIR / "Presets" / "User"
_DUBFORGE_DIR = _USER_DIR / "DUBFORGE"

ZSTD_LEVEL = 3  # compression level (1-22, 3 is default)

# ──────────────────────────────────────────────────────────────────────
# Real VST3 binary state bytes – captured from Serum 2 v2.1.1 via
# pedalboard (IComponent::getState / IEditController::getState).
# These are the init-patch defaults that Ableton passes to setState().
# ──────────────────────────────────────────────────────────────────────
_SERUM2_DEFAULT_PROCESSOR_STATE = bytes.fromhex(
    "5D8558C68CDBBB817FD81FFFFFFFFFFFFBDD84BD5AB00D9AB5495ACC884D87F9"
    "9BB8C558C8CD9AC4804A85F557CA0947E4704C85088BC9754B80C08CC8789885"
    "814BDC3D4BC43C8C90494B90C498BD354D88804A87F99BB9055C890987E47C53"
    "90859CB08887AC705BC7C158D0C15C55495BCA4D5AB4884D84788AC3784B86F8"
    "47D0819A8678879D019CBCC98DBBB05D95495BC54D57B88198CB8C57BB4D4A86"
    "F847D5495A8FC95B8678875D8558C4085390CD5AC50D5B86F847D5495BCA4D5A"
    "B4884DC3F88ABF39B34FFFFF07FFFFFDF46CBB339744E4307BF7C0C3420E7ECD"
    "730333070F3BA307146D39F761640497E9C94C65AA2341846D46A923E9C664AA"
    "2EF76910A8F251DC5FCB0134C82BD9AA13D766D6D47441D46B024017E1FFB1FF"
    "7645B080F308F1BB2E078255461FE0E7EFA68DD349B18CA79F9A9B9BD7B00641"
    "3B461FE0651E7867029289DDCA580CF41F1064113E10C57ED10F765D96F113BF"
    "74831878B804958E5BA71861862CC040BB0060D3067BC2B2D48C6811A815C946"
    "9F1050D0D06BEC118841F3CC23C6D0D9A767B4357C2215661F9C21C14F71CD82"
    "24882A4A9B373B2A3DBB2215669F908505B8247240647C7ACC156A1F90C73F5E"
    "4F1BC7021761235DC6791551A9F004A216BAF96542DA244CB3627A4614767D11"
    "924612B61FF8150D3EC51A02B15DC38B09A2A501101240C00748F36B13349619"
    "61461FE06514792388D94504502107CF33C8DDBA6EB4750BA78C73E76D2348DB"
    "2E1B3168CA248043A48A26CBCD7C918A7D2502107CF308F3BD655733FE73FD23"
    "CF2D2D97D33AC07E8A7B24FAA8AB9D68B7BCDAF53916261F0800030CF3FF5205"
    "713DAA904EC91F7A66D50A1BEA7B88152978E4E3989308A2B95F10CEACF7B159"
    "42B61F1FFF3C13C06470915C254D4DF393F8A8E8CF2ADA588DB763C980F669B2"
    "E1B356AB466C54458787DC57ADAE6F3CF05A4B85C51966056B453BBF544B5CC3"
    "5B6053C566BDF40EE6FF3CF365BC2CB6BAFDE7D55587A9ED2BE97F3FEA0457AA"
    "93ABAB4D498863877E476EC3F8E0AE50227FBB9BE8DAC4344AD6EECC722BA354"
    "779E8EABD5EAEE44A1943B5DF6DB35357E6FC69705A8A2EAE6ACEA9FFCD64854"
    "B4AE89E85CE9C25320B34EB30F5ADD3B9B34CB7A5A18486B6576CE97802EE4CF"
    "96AC33BA93F8DEB84B0767D92F419B55394C1DF89C529C1D00D00D08E38E1479"
    "FCC465308A0247F3575F77EF3CF7E7BD840F3CFFE07C036344F7228494F4AD9B"
    "D009FFD73693C3228F6C7B393031CD8504C5352FE5AF4B02E4A0568B4E904204"
    "7F747EC088D00578556B546E5B5F2E34E571E666662C4226ECDF34CBE5AB2626"
    "1F92909FC0E8DDB1C05A15C6A1AE824E10E8332CFFD4105E2636003C22CD21FF"
    "D892E4186BDD4D9D85A9A9CE2E2C92FA19848EDB71F2AF80704896D52FE1DC3F"
    "F91B7C2240A0DD76158121B555CBBB12DFCF953FCD5E599B996567F63A245A50"
    "94122DACF6D65224ED1070B5740A11FD14E2BE4E931B1A9012E3C1100A2922FE"
    "1DF52972B86623ADF39CEEA5BF13B00A72A26590F0D817C47EC8B8573C8E54B4"
    "6487E6D527FA194C97CCFF5FF1987338821F2A9CEBDC0AB90EF668519E8AAF78"
    "7CABC0003005FE80D003CAC569A5220ADD248ADE5F09F095439656DD61C1CA49"
    "E0F99B7A7524B8C35C3DB8FC0BD47E27E2AC38EF1B4E155982DF4F8B42118463"
    "318016E37B59B3B85BB10B2BF418D730FA3B"
)

_SERUM2_DEFAULT_CONTROLLER_STATE = bytes.fromhex(
    "5D8558C68CDBBB817FE82FFFFFFFFFFFFBDD84BD5AB00D9AB5495ACC884D84BD"
    "5AB5099BBB015A908987AC705980C1998678878CC898D5394CD7F48B85C098C9"
    "794C85C098DC714CCC7C8B848958C4B557BD7947AC705BC54D5B91058FD10199"
    "B88987E47847AC705BC54D5B91019090CD97C6415BCE4D5AB4884D84704A87F9"
    "9B90C598CF84D7B14947E47047B3F451B6415C7F304786F847BC8D9A8D4D97CC"
    "884D84B518C5459AC4704A87F99BB9055C890994908D9BA3C95A867887C7744B"
    "B47887AC745CC70947E47059CD019BCA8C8AB9F99890899B90CD5AC50D5BB4BD"
    "5AB3C847AC785C938158B88987E4705595495B7C75188BC95B8CC987AC785C90"
    "8D9BA3C95A86748BBF704BF1CCC0FFF7FFFFFFFF9D3E8AF02D50173D83FD7AF6"
    "9EC0979B0E3FFF37DF7DF7F714393FEFF008D317EC3356A88E1450B71B78F9A6"
    "64646416687F647B595553E16EB5C3ABBBCF9DE19D8FDF0A7FFA711106713F68"
    "0FD4FDBE30FFC2CE4F9EAACECADC600A7A5CC8D7634E596E4A7784B98E541A34"
    "D972BAAFACF3CD3135A0814F7C97E7F2EF76CD6A45A23C603587921BEEC52CCB"
    "C8FEF23D9432B62C96E18C73DDDE7C2452419911551C600A4E1102777F3E1225"
    "ECBC6C51E787195DCE46302282F9D220434B37E710A161EB354E665BBE17F5CA"
    "A9C6E57A47589604A30C0C4218CB6BA45119115E197459A121187FE208855954"
    "D3818000656BB90D207D4F8A930D02B5C91B88F96DE53463DAEAE27E549A3E71"
    "18A2B72751A9CCE7EB19EC0768D69FDEE23C6387FD5A62995D5275219CA426CE"
    "72AF97380FD38478552C8FB65D6CB7BF3765B7F47C02D45FA2029C75E98845AC"
    "6FF38685B121A4A7FEA3E56F730C4909F41C20E7AB0EC66A4CEAE305733DC1AB"
    "54A2F3EF051C21495EADAA1FFFC97AEDF406A116F23E75B9C5DDB1C89D673B85"
    "849029A8EC0F93FD27B62D0BE4067CD345D7D7C055D7F54F53E8B5B7109F7699"
    "EA1A46BF62066F4D4251BD3C832D17D545180DBC9849A43F3F47F7D38283E9E5"
    "097F64195F217052F7E5D9285BEFF51C495A114788F084C060814D7B632C3E8E"
    "25F67C523DE1ABE97870A5C3C515E3B9F7A1A7607B7673A5F86475FECE2A1AEE"
    "B742EAB2418B3F1CF863F7AEBF7FCB37FE8B2751A42A3BF951A8C778B529A1DE"
    "DB395E9D6D8E91811FDBAB8DEB6A91093F300956E135086FA4619E4C82522CB4"
    "1521E572F299D041A385D3FDEBC6399BFC0E8E24EE9F8403BD46F3704494DB31"
    "DA32FBD869A6E08295D7735E02"
)

# ──────────────────────────────────────────────────────────────────────
# VST3 state key sets – extracted from Serum 2 v2.1.1 via AU hosting
# ──────────────────────────────────────────────────────────────────────
# IComponent::getState() keys (162)
_PROCESSOR_KEYS: set[str] = {
    "Arp0",
    *(f"ArpClip{i}" for i in range(12)),
    "ClipPlayer0",
    *(f"Env{i}" for i in range(4)),
    *(f"FXRack{i}" for i in range(3)),
    "Global0",
    *(f"LFO{i}" for i in range(10)),
    *(f"LFOPointModBus{i}" for i in range(16)),
    *(f"Macro{i}" for i in range(8)),
    *(f"MidiClip{i}" for i in range(12)),
    *(f"ModSlot{i}" for i in range(64)),
    *(f"Oscillator{i}" for i in range(5)),
    "PitchQuantizer0",
    "RetriggerState0",
    *(f"RoutingSlot{i}" for i in range(7)),
    "VoiceFilter0", "VoiceFilter1",
    "VoicePanel0",
    # Metadata / config keys in processor CBOR
    "component", "lockOversampling", "lockTuning",
    "mpeConfig", "mpeEnabled", "mpePitchBendRange",
    "product", "productVersion", "scalars", "tags", "url",
    "vendor", "version",
}

# IEditController::getState() keys (58)
_CONTROLLER_KEYS: set[str] = {
    *(f"ArpClip{i}" for i in range(12)),
    "ClipPlayer",
    *(f"FXRack{i}" for i in range(3)),
    "Filter", "GranularOsc",
    *(f"LFO{i}" for i in range(10)),
    *(f"MidiClip{i}" for i in range(12)),
    "MultiSampleOsc", "Osc", "SerumGUI", "SpectralOsc",
    "VoicePanel0", "WTOsc",
    "arpBankDisplayName", "clipBankDisplayName",
    "component",
    "presetAuthor", "presetDescription", "presetHasBeenEdited", "presetName",
    "product", "productVersion", "url", "vendor", "version",
}

# JSON metadata templates for state blobs
_PROCESSOR_JSON_META = {
    "component": "processor",
    "product": "Serum2",
    "productVersion": "2.1.1",
    "url": "https://xferrecords.com/",
    "vendor": "Xfer Records",
    "version": 10.0,
}

_CONTROLLER_JSON_META = {
    "component": "controller",
    "presetAuthor": "",
    "presetDescription": "",
    "presetName": "",
    "product": "Serum2",
    "productVersion": "2.1.1",
    "url": "https://xferrecords.com/",
    "vendor": "Xfer Records",
    "version": 10.0,
}


def _build_xferjson_blob(json_meta: dict[str, Any],
                         cbor_data: dict[str, Any],
                         version: int = 2) -> bytes:
    """Assemble an XferJson state blob from JSON metadata and CBOR dict."""
    json_str = json.dumps(json_meta, separators=(",", ":"))
    json_bytes = json_str.encode("utf-8")
    cbor_raw = cbor2.dumps(cbor_data)
    cctx = zstandard.ZstdCompressor(level=ZSTD_LEVEL)
    compressed = cctx.compress(cbor_raw)
    payload = struct.pack("<II", len(cbor_raw), version) + compressed
    header = _MAGIC + struct.pack("<I", len(json_bytes)) + b"\x00\x00\x00\x00"
    return header + json_bytes + payload


# ──────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────
@dataclass
class SerumPreset:
    """In-memory representation of a Serum 2 preset."""

    name: str
    author: str = "DUBFORGE"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    product: str = "Serum2"
    product_version: str = "2.0.11"
    vendor: str = "Xfer Records"
    url: str = "https://github.com/ResonanceEnergy/DUBFORGE"
    version: float = 4.0
    # The actual CBOR dict with all 175 module keys
    cbor_data: dict[str, Any] = field(default_factory=dict)

    # ── Convenience parameter access ──────────────────────────────────

    def set_param(self, module: str, param: str, value: Any) -> None:
        """Set a single parameter on a module's plainParams dict.

        If the module's plainParams is the string ``"default"``, it is
        promoted to a dict first.
        """
        mod = self.cbor_data.get(module)
        if mod is None:
            self.cbor_data[module] = {"plainParams": {param: value}}
            return
        if not isinstance(mod, dict):
            return
        pp = mod.get("plainParams", "default")
        if pp == "default":
            mod["plainParams"] = {param: value}
        elif isinstance(pp, dict):
            pp[param] = value
        else:
            mod["plainParams"] = {param: value}

    def set_params(self, module: str, params: dict[str, Any]) -> None:
        """Set multiple parameters on a module at once."""
        for k, v in params.items():
            self.set_param(module, k, v)

    def set_sub_param(self, module: str, sub: str, param: str, value: Any) -> None:
        """Set a parameter on a sub-module (e.g. Oscillator0.WTOsc0)."""
        mod = self.cbor_data.setdefault(module, {"plainParams": "default"})
        if not isinstance(mod, dict):
            return
        sub_mod = mod.setdefault(sub, {"plainParams": "default"})
        if not isinstance(sub_mod, dict):
            return
        pp = sub_mod.get("plainParams", "default")
        if pp == "default":
            sub_mod["plainParams"] = {param: value}
        elif isinstance(pp, dict):
            pp[param] = value

    def set_mod_slot(self, slot: int, *,
                     dest_module_id: int | None = None,
                     dest_param_id: int | None = None,
                     dest_param_name: str = "",
                     dest_type: str = "",
                     source: str = "",
                     amount: float = 50.0,
                     bipolar: bool = False) -> None:
        """Configure a modulation slot."""
        key = f"ModSlot{slot}"
        entry: dict[str, Any] = {}
        if dest_module_id is not None:
            entry["destModuleID"] = dest_module_id
        if dest_param_id is not None:
            entry["destModuleParamID"] = dest_param_id
        if dest_param_name:
            entry["destModuleParamName"] = dest_param_name
        if dest_type:
            entry["destModuleTypeString"] = dest_type
        if source:
            entry["source"] = source
        params: dict[str, Any] = {"kParamAmount": amount}
        if bipolar:
            params["kParamBipolar"] = 1.0
        entry["plainParams"] = params
        self.cbor_data[key] = entry

    def get_metadata(self) -> dict[str, Any]:
        """Return the JSON metadata dict for the file header."""
        raw = json.dumps({
            "fileType": "SerumPreset",
            "hash": hashlib.md5(self.name.encode()).hexdigest(),
            "presetAuthor": self.author,
            "presetDescription": self.description,
            "presetName": self.name,
            "product": self.product,
            "productVersion": self.product_version,
            "tags": self.tags,
            "url": self.url,
            "vendor": self.vendor,
            "version": self.version,
        }, separators=(",", ":"))
        return raw

    # ── Serialization ─────────────────────────────────────────────────

    def to_cbor_bytes(self) -> bytes:
        """Serialize the preset dict to raw CBOR."""
        return cbor2.dumps(self.cbor_data)

    def to_file_bytes(self) -> bytes:
        """Produce the complete .SerumPreset binary."""
        # 1. JSON metadata
        json_str = self.get_metadata()
        json_bytes = json_str.encode("utf-8")

        # 2. CBOR → zstd compress
        cbor_raw = self.to_cbor_bytes()
        cctx = zstandard.ZstdCompressor(level=ZSTD_LEVEL)
        compressed = cctx.compress(cbor_raw)

        # 3. Binary payload: uint32 LE decompressed_size + uint32 LE version + zstd
        payload = struct.pack("<II", len(cbor_raw), 2) + compressed

        # 4. File: magic(9) + uint32 LE json_len + 4 zero bytes + json + payload
        header = _MAGIC + struct.pack("<I", len(json_bytes)) + b"\x00\x00\x00\x00"
        return header + json_bytes + payload

    def get_processor_state(self) -> bytes | None:
        """Return bytes for Ableton ALS ``<ProcessorState>`` embedding.

        Returns Ableton-native IBStream bytes captured from an Ableton-saved
        ALS file.  These are the Serum 2 init-patch defaults in XferJson
        format that Ableton's VST3 host can restore via setState().
        """
        from engine._captured_serum2_state import PROCESSOR_STATE_SERUM_2
        return PROCESSOR_STATE_SERUM_2

    def get_controller_state(self) -> bytes | None:
        """Return bytes for Ableton ALS ``<ControllerState>`` embedding.

        Returns Ableton-native IBStream bytes — paired with
        get_processor_state().
        """
        from engine._captured_serum2_state import CONTROLLER_STATE_SERUM_2
        return CONTROLLER_STATE_SERUM_2

    def write(self, path: str | Path) -> Path:
        """Write the preset to a .SerumPreset file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.to_file_bytes())
        _log.info("Wrote Serum 2 preset: %s (%d bytes)", p.name, p.stat().st_size)
        return p

    def install(self, subfolder: str = "DUBFORGE") -> Path:
        """Install the preset into Serum 2's User presets directory."""
        dest = _USER_DIR / subfolder
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / f"{self.name}.SerumPreset"
        out.write_bytes(self.to_file_bytes())
        _log.info("Installed preset to Serum 2: %s", out)
        return out


# ──────────────────────────────────────────────────────────────────────
# Reader
# ──────────────────────────────────────────────────────────────────────
def read_preset(path: str | Path) -> SerumPreset:
    """Read a .SerumPreset file into a SerumPreset object."""
    data = Path(path).read_bytes()
    if not data.startswith(b"XferJson"):
        raise ValueError(f"Not a Serum 2 preset: {path}")

    json_len = struct.unpack_from("<I", data, 9)[0]
    json_start = 17
    json_bytes = data[json_start:json_start + json_len]
    meta = json.loads(json_bytes)

    binary_offset = json_start + json_len
    remaining = data[binary_offset:]
    zstd_data = remaining[8:]  # skip decompressed_size(4) + version(4)

    dctx = zstandard.ZstdDecompressor()
    decompressed = dctx.decompress(zstd_data)
    cbor_data = cbor2.loads(decompressed)

    return SerumPreset(
        name=meta.get("presetName", ""),
        author=meta.get("presetAuthor", ""),
        description=meta.get("presetDescription", ""),
        tags=meta.get("tags", []),
        product=meta.get("product", "Serum2"),
        product_version=meta.get("productVersion", "2.0.11"),
        vendor=meta.get("vendor", "Xfer Records"),
        url=meta.get("url", ""),
        version=meta.get("version", 4.0),
        cbor_data=cbor_data,
    )


def clone_factory(relative_path: str, new_name: str) -> SerumPreset:
    """Clone a factory preset by relative path under Presets/Factory/.

    Example: ``clone_factory("Bass/Sub/BA - Sub Sustain - Low.SerumPreset",
                             "DUBFORGE_Fractal_Sub")``
    """
    src = _FACTORY_DIR / relative_path
    if not src.exists():
        raise FileNotFoundError(f"Factory preset not found: {src}")
    preset = read_preset(src)
    preset.name = new_name
    preset.author = "DUBFORGE"
    preset.description = "Generated by DUBFORGE — Planck x phi fractal basscraft"
    preset.url = "https://github.com/ResonanceEnergy/DUBFORGE"
    # Update metadata inside CBOR too
    preset.cbor_data["presetName"] = new_name
    preset.cbor_data["presetAuthor"] = "DUBFORGE"
    preset.cbor_data["presetDescription"] = preset.description
    return preset


# ──────────────────────────────────────────────────────────────────────
# DUBFORGE preset factory — one preset per track role
# ──────────────────────────────────────────────────────────────────────
PHI = 1.6180339887

# Map each DUBFORGE preset to a factory base + parameter overrides
_PRESET_RECIPES: dict[str, dict[str, Any]] = {
    "DUBFORGE_Fractal_Sub": {
        "base": "Bass/Sub/BA - Sub Sustain - Low.SerumPreset",
        "tags": ["Bass", "Sub", "Mono"],
        "params": {
            "Global0": {
                "kParamMonoToggle": 1.0,
                "kParamLegato": 1.0,
                "kParamPortamentoTime": 0.1 * PHI,
            },
            "Oscillator0": {"kParamOctave": -2.0},
        },
    },
    "DUBFORGE_Deep_Sub": {
        "base": "Bass/Sub/BA - Bent Woofer.SerumPreset",
        "tags": ["Bass", "Sub", "Deep"],
        "params": {
            "Global0": {"kParamMonoToggle": 1.0, "kParamLegato": 1.0},
            "Oscillator0": {"kParamOctave": -2.0},
        },
    },
    "DUBFORGE_Phi_Growl": {
        "base": "Bass/Hard/BA - Basilisk.SerumPreset",
        "tags": ["Bass", "Growl", "Aggressive"],
        "params": {},
    },
    "DUBFORGE_Spectral_Tear": {
        "base": "Bass/Modulated/MDL - Slippery Snake.SerumPreset",
        "tags": ["Bass", "Wobble", "Modulated"],
        "params": {},
    },
    "DUBFORGE_Riddim_Minimal": {
        "base": "Bass/Hard/BA - RM Wub Generator.SerumPreset",
        "tags": ["Bass", "Riddim", "Minimal"],
        "params": {
            "Global0": {"kParamMonoToggle": 1.0},
        },
    },
    "DUBFORGE_Formant_Vowel": {
        "base": "Vox/VOX - I Talk.SerumPreset",
        "tags": ["Vox", "Formant", "Vowel"],
        "params": {},
    },
    "DUBFORGE_Fibonacci_FM_Screech": {
        "base": "Lead/LD - Das EDM.SerumPreset",
        "tags": ["Lead", "FM", "Screech"],
        "params": {},
    },
    "DUBFORGE_Counter_Pluck": {
        "base": "Pluck/PL - Resonant Pluck.SerumPreset",
        "tags": ["Pluck", "Counter", "Melodic"],
        "params": {},
    },
    "DUBFORGE_Vocal_Fracture": {
        "base": "Vox/VOX - Granular Voices.SerumPreset",
        "tags": ["Vox", "Vocal", "Granular"],
        "params": {},
    },
    "DUBFORGE_Golden_Reese": {
        "base": "Bass/Reese/BA - Gnarly Reese.SerumPreset",
        "tags": ["Bass", "Reese", "Chord"],
        "params": {},
    },
    "DUBFORGE_Granular_Atmosphere": {
        "base": "Pad/PD - Ether.SerumPreset",
        "tags": ["Pad", "Atmosphere", "Granular"],
        "params": {},
    },
    "DUBFORGE_Phi_Arp": {
        "base": "Arp/ARP - Daftronic.SerumPreset",
        "tags": ["Arp", "Synth", "Rhythmic"],
        "params": {},
    },
    "DUBFORGE_Weapon": {
        "base": "SFX/FX - Demon Woosh.SerumPreset",
        "tags": ["SFX", "Impact", "Weapon"],
        "params": {},
    },
    "DUBFORGE_Riser_Sweep": {
        "base": "SFX/FX - Wasp Whistle Sweep.SerumPreset",
        "tags": ["SFX", "Riser", "Sweep"],
        "params": {},
    },
}


def build_preset(name: str) -> SerumPreset:
    """Build a DUBFORGE preset by name using the recipe registry."""
    recipe = _PRESET_RECIPES.get(name)
    if recipe is None:
        raise KeyError(f"No recipe for preset: {name}")
    preset = clone_factory(recipe["base"], name)
    preset.tags = recipe.get("tags", [])
    # Apply parameter overrides
    for module, params in recipe.get("params", {}).items():
        preset.set_params(module, params)
    return preset


def build_all_presets() -> dict[str, SerumPreset]:
    """Build all DUBFORGE presets. Returns {name: SerumPreset}."""
    result = {}
    for name in _PRESET_RECIPES:
        try:
            result[name] = build_preset(name)
        except FileNotFoundError as exc:
            _log.warning("Skipping %s: %s", name, exc)
    return result


def install_all_presets() -> list[Path]:
    """Build and install all DUBFORGE presets to Serum 2's User folder."""
    paths = []
    for name, preset in build_all_presets().items():
        try:
            paths.append(preset.install())
        except OSError as exc:
            _log.warning("Failed to install %s: %s", name, exc)
    return paths


def get_preset_state_map() -> dict[str, tuple[bytes, bytes]]:
    """Return ``{preset_name: (processor_state, controller_state)}`` for all presets.

    The bytes are XferJson state blobs ready for base64-encoding into ALS
    ``<ProcessorState>`` and ``<ControllerState>`` elements.
    """
    result: dict[str, tuple[bytes, bytes]] = {}
    for name, preset in build_all_presets().items():
        result[name] = (preset.get_processor_state(),
                        preset.get_controller_state())
    return result


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1 and sys.argv[1] == "install":
        paths = install_all_presets()
        print(f"Installed {len(paths)} presets to {_DUBFORGE_DIR}")
        for p in paths:
            print(f"  {p.name}")
    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        for name in sorted(_PRESET_RECIPES):
            print(f"  {name} <- {_PRESET_RECIPES[name]['base']}")
    else:
        print("Usage: python -m engine.serum2_preset [install|list]")
        print(f"  install — Build & install {len(_PRESET_RECIPES)} DUBFORGE presets to Serum 2")
        print(f"  list    — Show preset recipes")
