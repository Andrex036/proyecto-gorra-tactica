"""Empaqueta la geometría evaluada de Blender para el visor web sin dependencias.

python pack_model.py ruta/visor-data.json ../dist/js/model-data.js
"""
import argparse
import base64
import json
import struct
import zlib
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('input', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
parts = json.loads(args.input.read_text())
header = []
data = bytearray()
vertices = triangles = 0
for part in parts:
    count, index_count, offset = len(part['p']) // 3, len(part['i']), len(data)
    positions = [round(value * 1000) for value in part['p']]
    assert all(-32767 <= value <= 32767 for value in positions), 'Position outside packed range'
    normal_bits = part.get('normal_bits', 8)
    normal_max = 32767 if normal_bits == 16 else 127
    normals = [max(-normal_max, min(normal_max, round(value * normal_max))) for value in part['v']]
    assert len(normals) == len(positions)
    assert max(part['i']) < count
    data.extend(struct.pack('<' + 'h' * len(positions), *positions))
    data.extend(struct.pack(('<' + 'h' * len(normals)) if normal_bits == 16 else ('b' * len(normals)), *normals))
    data.extend(struct.pack('<' + 'I' * index_count, *part['i']))
    uv=part.get('uv',[])
    assert len(uv)==count*2, 'Missing textile UV coordinates'
    data.extend(struct.pack('<'+'f'*len(uv),*uv))
    header.append([part['n'], count, index_count, offset,
                   [round(value, 3) for value in part['c']], part['g'], part['d'], True, part['role']])
    if normal_bits == 16:header[-1].append(16)
    vertices += count
    triangles += index_count // 3
encoded_header = json.dumps(header, separators=(',', ':')).encode()
payload = struct.pack('<I', len(encoded_header)) + encoded_header + data
encoded = base64.b64encode(zlib.compress(payload, 9)).decode()
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text("window.GORRA_MODEL_DATA = '" + encoded + "';\n")
print(json.dumps({'meshes': len(parts), 'vertices': vertices, 'triangles': triangles,
                  'groups': len(set(part['g'] for part in parts)), 'bytes': args.output.stat().st_size}))
