extends RefCounted
# Preserve existing QA entry flags while keeping one current set of assertions.
static func run(app,folder: String):
	await preload("res://tests/theatre_ui_qa.gd").run(app,folder)
