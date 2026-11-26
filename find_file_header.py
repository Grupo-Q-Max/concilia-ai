import os

desktop = "C:/Users/RodrigoSantePenhalve/Desktop"

try:
    for fname in os.listdir(desktop):
        full = os.path.join(desktop, fname)
        if os.path.isfile(full):
            sz = os.path.getsize(full)
            if "178" in fname or "final" in fname.lower() or "razão" in fname.lower() or "razao" in fname.lower():
                print(f"Found: {full} | Size: {sz} bytes")
                with open(full, "rb") as f:
                    header = f.read(32)
                    print(f"  Header bytes: {header}")
                    print(f"  Header hex:   {header.hex()}")
except Exception as e:
    print("Desktop error:", e)
