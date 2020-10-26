def find_closest_number(n, ns):
    # Return the number from `ns` that is closest to `n`
    return min(ns, key=lambda x: abs(x - n))
