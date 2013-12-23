import datetime
import itertools

def sorted_groupby(list_, key_):
	return [(supirior, list(inferior)) for supirior, inferior in itertools.groupby(sorted(list_, key=key_), key=key_)]

def is_nan(f):
	return f!=f

def to_date(string):
	return datetime.datetime.strptime(string, "%m/%d/%Y").date()

def find_nearest(value, rng, on_tie=None):
	return find_nearest_of(value, rng, lambda x: x, on_tie)

#TODO: did not deal with ties before. need to look at uses and correct for ties. Remove the default arg to catch them!
def find_nearest_of(value, rng, key, on_tie=None):
	""" Returns the nearest value in range by taking the absolute difference of it and all other values. """

	#default behavior is to just return the first of the tie
	if not on_tie:
		on_tie = lambda x: x[0]

	rng = list(rng)

	minimum = min([abs(key(v) - value) for v in rng])
	return on_tie([v for v in rng if abs(key(v) - value) == minimum])

