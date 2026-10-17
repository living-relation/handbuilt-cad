from build123d import *
import pedal_adapter as pa
pad = pa.prism_xy(pa.PAD_LEFT, 50, 53)
print("pad vol", pad.volume, pad.bounding_box())
c = pa.cyl_z(*pa.PAD_CENTER, pa.PAD_DIA, 50, 53); print("cyl", c.volume, c.bounding_box())
st = pa.box_between(-400, 400, pa.LID_STEP_Y_MIN, 400, pa.Z_LID, pa.Z_PAD + 1) - (pad + c)
print("step vol", st.volume)
fo = pa.prism_xy(pa.FRONT_OUTLINE, 0, 1); print("front", fo.volume)
