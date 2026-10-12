extends SceneTree
const WeaponAudio=preload("res://scripts/weapon_audio.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var checks: Array=[];var rows: Array=[];var hashes: Dictionary={}
	for family in ["bow","crossbow","drum","ritual"]:
		var stream: AudioStreamWAV=WeaponAudio.sample(family);var peak: int=0;var energy: float=0
		for i in range(stream.data.size()/2):
			var value: int=stream.data.decode_s16(i*2);peak=maxi(peak,absi(value));energy+=float(value)*value
		var digest: String=stream.data.hex_encode().sha256_text();hashes[digest]=true
		var duration: float=float(stream.data.size())/2/stream.mix_rate
		var error: int=stream.save_to_wav(folder+"/"+family+".wav")
		checks.append({"name":family+" finite non-clipping short PCM", "passed":error==OK and peak>1000 and peak<24576 and duration>.09 and duration<=.26})
		rows.append({"family":family,"peak":peak,"rms":sqrt(energy/(stream.data.size()/2)),"seconds":duration,"sample_sha256":digest})
	checks.append({"name":"four distinct sounds","passed":hashes.size()==4})
	for row in [["archer","combat-bow"],["repeater","combat-crossbow"],["sniper","combat-crossbow"],["drummer","combat-drum"],["scribe","combat-ritual"],["artillery","combat-cannon"],["javelin","combat-throw"]]:
		checks.append({"name":"real attack role "+row[0],"passed":WeaponAudio.event_name({"weapon_role":row[0],"ranged":true})==row[1]})
	var failures: Array=checks.filter(func(c):return not c.passed)
	for row in [["javelin","crossbow"],["artillery","ballista"]]:
		checks.append({"name":"equipment overrides old role "+row[1],"passed":WeaponAudio.event_name({"weapon_role":row[0],"weapon_gesture":row[1],"ranged":true})=="combat-crossbow"})
	failures=checks.filter(func(c):return not c.passed)
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"samples":rows,"scope":"PCM range and attack-role routing; not speaker loudness or listening review.","inputs":{}}
	for path in ["res://scripts/weapon_audio.gd","res://scripts/audio_synth.gd","res://scripts/audio_controller.gd","res://tests/test_weapon_audio.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("WEAPON_AUDIO ",checks.size()," checks / ",failures.size()," failures");quit(0 if failures.is_empty() else 1)
