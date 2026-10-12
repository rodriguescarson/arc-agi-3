# CPU-only probe v2: print the loader / quant-method code paths that decide whether an AutoRound
# checkpoint with quantized attention + linear-attention projections (Swift-1.5) loads into
# Pennyroyal's fused qwen4_exp modules.
import glob, zipfile, re
wh = glob.glob("/kaggle/input/**/sglang-*.whl", recursive=True)
z = zipfile.ZipFile(wh[0])
def show(name, ranges):
    src = z.read(name).decode().splitlines()
    print("\n" + "=" * 100 + f"\n{name}\n" + "=" * 100)
    for a, b in ranges:
        for i in range(a - 1, min(b, len(src))):
            print(f"{i+1:5d}: {src[i]}")
        print("      ...")
show("sglang/srt/layers/quantization/auto_round.py", [(55, 120), (150, 290), (540, 575)])
show("sglang/srt/models/qwen4_exp.py", [(425, 445), (495, 510), (800, 830), (925, 975), (1330, 1365), (1605, 1640), (2020, 2110), (2200, 2260)])
# Any packed_modules_mapping for this model?
src = z.read("sglang/srt/models/qwen4_exp.py").decode()
for m in re.finditer(r"packed_modules_mapping[\s\S]{0,600}", src):
    print("PACKED:", m.group(0)[:600]); break
for n in z.namelist():
    if n.endswith("qwen3_5.py") or n.endswith("qwen3_next.py"):
        s2 = z.read(n).decode()
        m = re.search(r"packed_modules_mapping[\s\S]{0,500}", s2)
        print("\n", n, "PACKED:", m.group(0)[:500] if m else None)
