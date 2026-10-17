"""Combine <prefix>_{front,back,left,right,top,bottom}.png into <prefix>_sheet.png. Usage: python tools/sheet.py <prefix>"""
import sys; from PIL import Image
p = sys.argv[1]; ims = [Image.open(f'{p}_{n}.png').convert('RGB') for n in ('front', 'back', 'left', 'right', 'top', 'bottom')]
W, H = ims[0].size; s = Image.new('RGB', (3 * W, 2 * H), 'white')
for i, im in enumerate(ims): s.paste(im, ((i % 3) * W, (i // 3) * H))
s.save(f'{p}_sheet.png')
