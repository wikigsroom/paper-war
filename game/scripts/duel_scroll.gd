extends "res://scripts/mobile_scroll.gd"
var block_input: Callable

func input_blocked() -> bool:
	return super.input_blocked() or (block_input.is_valid() and block_input.call())
