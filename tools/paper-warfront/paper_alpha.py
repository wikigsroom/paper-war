"""Remove gateway matte fringe at the alpha boundary, retaining interior paint."""
import numpy as np
from scipy import ndimage
from PIL import Image
def defringe(image):
    a=np.array(image.convert('RGBA'));mask=a[:,:,3]>48
    inner=ndimage.binary_erosion(mask,iterations=2)
    if not inner.any():return image
    red=(a[:,:,0]>130)&(a[:,:,0].astype(float)>a[:,:,1]*1.7)&(a[:,:,0].astype(float)>a[:,:,2]*1.7)
    bad=mask&~inner&red
    if bad.any():
        _,indices=ndimage.distance_transform_edt(~inner,return_indices=True)
        colors=a[indices[0],indices[1],:3]
        a[bad,:3]=colors[bad]
    a[a[:,:,3]==0,:3]=0
    return Image.fromarray(a)
