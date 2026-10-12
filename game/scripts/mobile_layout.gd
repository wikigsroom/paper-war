extends RefCounted
# Layout coordinates are Android density-independent units, not desktop pixels.
const TOUCH=48.0
const GAP=8.0

static func measure(pixels: Vector2,dpi: float,safe_pixels: Rect2) -> Dictionary:
	var density: float=clampf(dpi/160.0,.75,4.0) if dpi>0 else 1.0
	var window: Rect2=Rect2(Vector2.ZERO,pixels)
	var safe: Rect2=window.intersection(safe_pixels) if safe_pixels.has_area() else window
	if not safe.has_area():safe=window
	var viewport: Vector2=Vector2(roundf(pixels.x/density),roundf(pixels.y/density))
	# Match the actual canvas transform after integer content_scale_size rounding.
	var ratio: Vector2=viewport/pixels
	var bounds: Rect2=Rect2(safe.position*ratio,safe.size*ratio)
	var gutter: float=8.0 if bounds.size.x<900 else 16.0
	return {"density":density,"pixels":pixels,"viewport":viewport,"safe":bounds,"content":bounds.grow(-gutter),"portrait":pixels.y>pixels.x,"gutter":gutter}

static func columns(width: float,minimum: float=200.0,maximum: int=3) -> int:
	return clampi(int((width+GAP)/(minimum+GAP)),1,maximum)
