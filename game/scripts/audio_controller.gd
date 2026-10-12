extends Node

var settings: Dictionary = {"music":.45,"sfx":.7}
var pool: Array = []
var music: AudioStreamPlayer
var streams: Dictionary = {}
var clocks: Dictionary = {}
var silent: bool = false
var background: bool=false
var music_faction: String = ""
var current_time: float = 0
var runtime_alert: AudioStreamWAV
const Synth = preload("res://scripts/audio_synth.gd")
const WeaponAudio=preload("res://scripts/weapon_audio.gd")

func _ready():
	silent=DisplayServer.get_name()=="headless"
	if silent: return
	var limiter=AudioEffectLimiter.new();limiter.threshold_db=-6;limiter.ceiling_db=-1
	AudioServer.add_bus_effect(0,limiter)
	for i in range(16):
		var player=AudioStreamPlayer.new()
		add_child(player); pool.append(player)
	music=AudioStreamPlayer.new(); add_child(music)
	runtime_alert=synthesize_warning()
	streams["state-route"]=synthesize_state(310,.17,false)
	streams["state-complete"]=synthesize_state(440,.3,true)
	streams["state-disabled"]=synthesize_state(140,.23,false)
	streams["worker-pick"]=synthesize_state(780,.095,false)
	streams["worker-load"]=synthesize_state(530,.14,true)
	for family in ["bow","crossbow","drum","ritual"]:streams["combat-"+family]=WeaponAudio.sample(family)

func synthesize_state(base: float,duration: float,rising: bool) -> AudioStreamWAV:
	var rate: int = 22050;var bytes=PackedByteArray();bytes.resize(int(rate*duration)*2)
	var rng=RandomNumberGenerator.new();rng.seed=int(base)
	for i in range(bytes.size()/2):
		var t: float = float(i)/rate;var ratio: float = t/duration
		var frequency: float = base*(1+ratio*.35 if rising else 1-ratio*.2)
		var tap: float = fmod(t,.075);var envelope: float = exp(-tap*42)*pow(1-ratio,1.4)
		var sample: float = (Synth.triangle(frequency*t)*.32+sin(TAU*frequency*2*t)*.15+rng.randf_range(-.07,.07))*envelope
		bytes.encode_s16(i*2,int(clampf(sample,-.8,.8)*32767))
	var stream=AudioStreamWAV.new();stream.mix_rate=rate;stream.format=AudioStreamWAV.FORMAT_16_BITS;stream.data=bytes;return stream

func synthesize_warning() -> AudioStreamWAV:
	var rate=22050
	var samples=PackedByteArray(); samples.resize(int(rate*.38)*2)
	for i in range(samples.size()/2):
		var t=float(i)/rate
		var envelope=Synth.sfx_envelope(t,.38,.016,.75)*pow(maxf(0.0,1-t/.38),2)
		var v=(sin(TAU*(190*t-65*t*t))*.65+sin(TAU*380*t)*.22)*envelope*.45
		samples.encode_s16(i*2,int(clampf(v,-.8,.8)*32767))
	var stream=AudioStreamWAV.new(); stream.format=AudioStreamWAV.FORMAT_16_BITS; stream.mix_rate=rate; stream.data=samples
	return stream

func _process(delta):
	if background:return
	current_time+=delta
	if music and music.playing: music.volume_db=linear_to_db(float(settings.music)*.48)

func play(name: String, power: float = 1.0):
	if silent or background or float(settings.sfx)<=0: return
	var spacing=.07 if name.begins_with("combat") else .04
	if current_time-float(clocks.get(name,-100))<spacing: return
	clocks[name]=current_time
	if not streams.has(name):
		var path="res://assets/audio/sfx/audio-"+name+".wav"
		if not ResourceLoader.exists(path): return
		streams[name]=load(path)
	for player in pool:
		if player.playing: continue
		player.stream=streams[name]
		player.volume_db=linear_to_db(maxf(.001,float(settings.sfx)*clampf(power,.25,1.0)*.65))
		player.pitch_scale=1.0+sin(current_time*37)*.035
		if name=="combat-heavy": player.pitch_scale=.91+clampf(power,0,1)*.05
		player.play(); return

func set_music(faction: String):
	if silent or music_faction==faction: return
	music_faction=faction
	var path="res://assets/audio/music/music-"+faction+".wav"
	if not ResourceLoader.exists(path): path="res://assets/audio/music/music-yin.wav"
	var stream=load(path) as AudioStreamWAV
	if stream==null: return
	stream.loop_mode=AudioStreamWAV.LOOP_FORWARD
	stream.loop_begin=0; stream.loop_end=stream.data.size()/2
	music.stream=stream; music.volume_db=linear_to_db(float(settings.music)*.48); music.play()

func danger():
	if silent or background or float(settings.sfx)<=0 or current_time-float(clocks.get("danger",-100))<7: return
	clocks["danger"]=current_time
	for player in pool:
		if not player.playing:
			player.stream=runtime_alert; player.volume_db=linear_to_db(maxf(.001,float(settings.sfx)*.5)); player.pitch_scale=1; player.play(); break

func battle_event(e: Dictionary, camera: float):
	if e.get("side",0)!=0 and e.kind in ["gold","recruit","research_start","research_done","cancel"]: return
	if e.has("x") and absf(float(e.x)-camera)>14 and e.kind in ["hit","attack","death"]: return
	match e.kind:
		"economy_alarm":danger()
		"mine_strike":
			if absf(float(e.x)-camera)<11:play("worker-pick",.28)
		"cargo_loaded":
			if absf(float(e.x)-camera)<11:play("worker-load",.22)
		"route_changed","mine_priority":
			if e.get("side",0)==0:play("state-route",.55)
		"building_completed":
			if e.get("side",0)==0:play("state-complete",.7)
		"facility_disabled":play("state-disabled",.65)
		"hit": play("combat-heavy" if e.heavy else "combat-hit",clampf(float(e.amount)/45,.35,1))
		"death": play("combat-death",.6)
		"attack": play(WeaponAudio.event_name(e),.78 if e.heavy else .60)
		"reload":
			if absf(float(e.x)-camera)<14:play("combat-crossbow",.22)
		"unit_special":play("combat-ritual",.38)
		"recruit": play("ui-recruit")
		"research_done": play("ui-research")
		"cancel": play("ui-cancel")
		"gold": play("ui-gold",.4)
		"cast":
			var faction=e.id.get_slice(".",1)
			play("magic-repair" if e.id.ends_with("repair") else ("magic-ink" if faction=="mo" else ("magic-clone" if e.id.ends_with("clone") else "magic-seal")))
		"building_death": play("combat-heavy")
		"result": play("result-victory" if e.winner==0 else "result-defeat")

func set_background(value: bool):
	background=value
	if music:music.stream_paused=value
	if value:
		for player in pool:player.stop()
