"""Inspect the factory template's device structure."""
import gzip
import xml.etree.ElementTree as ET

path = r"C:\ProgramData\Ableton\Live 12 Standard\Resources\Builtin\Templates\DefaultLiveSet.als"
with gzip.open(path, "rb") as f:
    tree = ET.parse(f)
root = tree.getroot()

for delay in root.iter("Delay"):
    print("=== Delay direct children (top-level device structure) ===")
    for child in delay:
        attrs = " ".join(f'{k}="{v}"' for k, v in child.attrib.items())
        if len(child) == 0:
            print(f"  <{child.tag} {attrs} />")
        else:
            print(f"  <{child.tag} {attrs}>")
            for gc in child:
                ga = " ".join(f'{k}="{v}"' for k, v in gc.attrib.items())
                if len(gc) == 0:
                    print(f"    <{gc.tag} {ga} />")
                else:
                    print(f"    <{gc.tag} {ga}> ...")
    break

print()
print("=== Our PluginDevice children ===")
# Compare with our generated PluginDevice
pd_xml = """<PluginDevice Id="0">
<LomId Value="0" /><LomIdView Value="0" /><IsExpanded Value="true" />
<On><LomId Value="0" /><Manual Value="true" /><AutomationTarget Id="100"><LockEnvelope Value="0" /></AutomationTarget><MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds></On>
<ParametersListWrapper LomId="0" /><LastPresetRef><Value /></LastPresetRef><LockedScripts />
<IsFolded Value="false" /><ShouldShowPresetName Value="true" /><UserName Value="" /><Annotation Value="" />
<SourceContext><Value /></SourceContext>
<PluginDesc><Vst3PluginInfo Id="0">
<WinPosX Value="0" /><WinPosY Value="0" /><TransportFlags Value="7" />
<Uid><Fields><Field1 Value="1448297816" /><Field2 Value="1718833267" /><Field3 Value="1701999981" /><Field4 Value="540147712" /></Fields></Uid>
<DeviceType Value="1" /><Name Value="Serum 2" /><Vendor Value="Xfer Records" /><Category Value="Instrument|Synth" />
</Vst3PluginInfo></PluginDesc>
<Name Value="Serum 2" /><ParameterList />
</PluginDevice>"""
pd = ET.fromstring(pd_xml)
for child in pd:
    attrs = " ".join(f'{k}="{v}"' for k, v in child.attrib.items())
    if len(child) == 0:
        print(f"  <{child.tag} {attrs} />")
    else:
        print(f"  <{child.tag} {attrs}>")
