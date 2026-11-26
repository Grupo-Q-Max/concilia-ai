# Let's inspect known file signatures
import struct

magic = b'\x01\x02\x06\x00\x00\x00\x0c\x00'
print("Magic hex:", magic.hex())
print("Unpacked short:", struct.unpack('<H', magic[:2])[0])
print("Unpacked int:", struct.unpack('<I', magic[:4])[0])
