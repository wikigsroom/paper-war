extends SceneTree

func _initialize():
	var main_notice=FileAccess.open("res://licenses/GODOT-LICENSE.txt",FileAccess.WRITE)
	main_notice.store_string(Engine.get_license_text()); main_notice.close()
	var notice=FileAccess.open("res://licenses/GODOT-COPYRIGHT.txt",FileAccess.WRITE)
	notice.store_string("Godot Engine %s third-party notices\n\n"%Engine.get_version_info().string)
	for entry in Engine.get_copyright_info():
		notice.store_string(str(entry.name)+"\n")
		for part in entry.parts:
			notice.store_string("Files: "+", ".join(part.files)+"\n")
			notice.store_string("\n".join(part.copyright)+"\nLicense: "+str(part.license)+"\n\n")
	notice.store_string("FULL LICENSE TEXTS\n\n")
	var licenses=Engine.get_license_info()
	for key in licenses:
		notice.store_string(str(key)+"\n\n"+str(licenses[key])+"\n\n")
	notice.close()
	print("Engine and third-party notices exported from native Godot engine.")
	quit()
