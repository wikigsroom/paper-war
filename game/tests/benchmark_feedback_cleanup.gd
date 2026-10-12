extends SceneTree
func _initialize():call_deferred("run")
func measure(compact: bool) -> int:
	var total: int=0
	for round_index in range(1000):
		var items: Array=[]
		for i in range(650):items.append({"life":.01 if i%2==0 else 1.0})
		var start: int=Time.get_ticks_usec()
		if compact:
			var alive: int=0
			for item in items:
				item.life-=.02
				if item.life>0:items[alive]=item;alive+=1
			items.resize(alive)
		else:
			for item in items.duplicate():
				item.life-=.02
				if item.life<=0:items.erase(item)
		total+=Time.get_ticks_usec()-start
	return total
func run():
	measure(false);measure(true)
	var old: Array=[];var improved: Array=[]
	for sample in range(5):
		old.append(measure(false));improved.append(measure(true))
	old.sort();improved.sort()
	var result={"old_us":old,"compact_us":improved,"median_ratio":float(old[2])/maxi(1,improved[2]),"elements":650,"updates_per_sample":1000,"samples":5,"scope":"Windows native headless isolated cleanup microbenchmark, allocation of input excluded. Does not measure battle rendering or Android FPS."}
	var args=OS.get_cmdline_user_args()
	FileAccess.open(args[args.find("--report")+1],FileAccess.WRITE).store_string(JSON.stringify(result,"\t"))
	print(JSON.stringify(result));quit()
