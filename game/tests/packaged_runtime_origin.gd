extends SceneTree
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();var report={"version":ProjectSettings.get_setting("application/config/version"),"inputs":{},"source_gameplay_files_absent":true}
	for name in ["tactical_ai","mobile_ui","recruitment_readiness","local_duel","network_commands","battle_command_rules","ui_battle_sheets","battle_view","battle_visibility","theatre_fog"]:
		var path: String="res://scripts/"+name+".gdc"
		if FileAccess.file_exists(path):
			report.inputs[path]=FileAccess.get_sha256(path)
			report.source_gameplay_files_absent=report.source_gameplay_files_absent and not FileAccess.file_exists("res://scripts/"+name+".gd")
	for path in ["res://scripts/battle_sim.gdc","res://scripts/data_store.gdc","res://scripts/main.gdc","res://scripts/match_projection.gdc","res://data/balance-prototype.json","res://data/technology.json","res://data/maps.json"]:
		assert(FileAccess.file_exists(path),"Packaged resource missing")
		report.inputs[path]=FileAccess.get_sha256(path)
	for name in ["battle_sim","data_store","main","match_projection"]:
		report.source_gameplay_files_absent=report.source_gameplay_files_absent and not FileAccess.file_exists("res://scripts/"+name+".gd")
	assert(report.source_gameplay_files_absent)
	FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("PACKAGED_RUNTIME_ORIGIN true");quit()
