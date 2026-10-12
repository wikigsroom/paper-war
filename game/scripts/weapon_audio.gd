extends RefCounted
const Synth=preload("res://scripts/audio_synth.gd")
# Cached short PCM samples: dry paper/wood attacks, separate from hit feedback.
static func sample(family: String) -> AudioStreamWAV:
	var rate: int=22050;var duration: float=.18 if family=="bow" else .12 if family=="crossbow" else .25
	var bytes=PackedByteArray();bytes.resize(int(duration*rate)*2)
	var rng=RandomNumberGenerator.new();rng.seed=2907+family.length()
	var filtered: float=0
	for i in range(bytes.size()/2):
		var t: float=float(i)/rate;var noise: float=rng.randf_range(-1,1)
		filtered=lerpf(filtered,noise,.20)
		var value: float=0
		match family:
			"bow":value=(sin(TAU*(230*t-120*t*t))*.22+sin(TAU*460*t)*.11+filtered*.18)*exp(-t*28)
			"crossbow":value=(noise*.33*exp(-t*110)+sin(TAU*570*t)*.15*exp(-t*43)+filtered*.10*exp(-t*25))
			"drum":value=(sin(TAU*(105*t-95*t*t))*.38+noise*.10*exp(-t*70))*exp(-t*18)
			_:value=(sin(TAU*440*t)*.16+sin(TAU*660*t)*.10+sin(TAU*880*t)*.04)*exp(-t*15)
		value*=Synth.sfx_envelope(t,duration,.02,.35)
		bytes.encode_s16(i*2,int(clampf(value,-.75,.75)*32767))
	var stream=AudioStreamWAV.new();stream.mix_rate=rate;stream.format=AudioStreamWAV.FORMAT_16_BITS;stream.data=bytes;return stream

static func event_name(e: Dictionary) -> String:
	var gesture: String=str(e.get("weapon_gesture",""))
	if gesture in ["crossbow","ballista"]:return "combat-crossbow"
	if gesture=="bow":return "combat-bow"
	match str(e.get("weapon_role","")):
		"artillery","mortar":return "combat-cannon"
		"archer":return "combat-bow"
		"repeater","sniper":return "combat-crossbow"
		"drummer":return "combat-drum"
		"medic","oracle","scribe","necromancer","summoner","illusionist","burner","caravan":return "combat-ritual"
	return "combat-throw" if e.ranged else "combat-slash"
