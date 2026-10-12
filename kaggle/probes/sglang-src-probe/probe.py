# CPU-only probe v4: the custom packed weight loader of Qwen3_5GatedDeltaNet (in_proj_qkvz /
# in_proj_ba) and the generic column-parallel loader it may delegate to.  Decides whether a
# GPTQ/AutoRound-packed in_proj (Swift-1.5) can be loaded head-first.
import glob, zipfile, re
wh = glob.glob("/kaggle/input/**/sglang-*.whl", recursive=True)
z = zipfile.ZipFile(wh[0])
def dump(name, a, b):
    src = z.read(name).decode().splitlines()
    print("\n" + "=" * 100 + f"\n{name} [{a}-{b}] of {len(src)}\n" + "=" * 100)
    for i in range(a - 1, min(b, len(src))):
        print(f"{i+1:5d}: {src[i]}")
dump("sglang/srt/models/qwen3_5.py", 411, 602)
src = z.read("sglang/srt/models/qwen3_5.py").decode().splitlines()
for i, line in enumerate(src):
    if "def _bind_packed_weight_loaders" in line or "def _override_weight_loader" in line:
        dump("sglang/srt/models/qwen3_5.py", i + 1, i + 60)
lin = z.read("sglang/srt/layers/linear.py").decode().splitlines()
print("\nlinear.py packed-dim handling:")
for i, line in enumerate(lin):
    if re.search(r"packed_dim|pack_factor|packed_factor|output_dim|is_gguf|def weight_loader|class ColumnParallelLinear|class MergedColumnParallelLinear|class QKVParallelLinear", line):
        print(f"{i+1:5d}: {line}")
