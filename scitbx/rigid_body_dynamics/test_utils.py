from scitbx import matrix

def potential_energy(sites, wells, A, J, AJA_tree=None):
  result = 0
  AJA = A.Tb0 * J.Tsp * A.T0b
  if (AJA_tree is not None): AJA = AJA_tree * AJA
  for s, w in zip(sites, wells):
    result += (AJA * s - w).dot()
  return result

def potential_f_ext_ff(sites, wells, A, J, AJA_tree=None):
  AJA = A.Tb0 * J.Tsp * A.T0b
  if (AJA_tree is not None): AJA = AJA_tree * AJA
  f_cart = [-2 * (AJA * s - w) for s, w in zip(sites, wells)]
  f = matrix.col((0,0,0))
  nc = matrix.col((0,0,0))
  for s,force in zip(sites, f_cart):
    f += force
    nc += (AJA * s).cross(force)
  return matrix.col((nc, f)).resolve_partitions()

def potential_energy_bf(sites, wells, A, J, AJA_tree=None):
  result = 0
  JA = J.Tps * A.T0b
  if (AJA_tree is not None): JA *= AJA_tree.inverse()
  for s, w in zip(sites, wells):
    result += (A.T0b * s - JA * w).dot()
  return result

def potential_f_ext_bf(sites, wells, A, J, AJA_tree=None):
  JA = J.Tps * A.T0b
  if (AJA_tree is not None): JA *= AJA_tree.inverse()
  f_cart = [-2 * (A.T0b * s - JA * w) for s, w in zip(sites, wells)]
  f = matrix.col((0,0,0))
  nc = matrix.col((0,0,0))
  for s,force in zip(sites, f_cart):
    f += force
    nc += (A.T0b * s).cross(force)
  return matrix.col((nc, f)).resolve_partitions()

def create_wells(sites, mersenne_twister, r=None):
  "overall random rotation and translation + noise"
  if (r is None):
    r = matrix.sqr(mersenne_twister.random_double_r3_rotation_matrix())
  t = matrix.col(mersenne_twister.random_double(size=3)-0.5)
  wells = []
  for site in sites:
    t_noise = t + matrix.col(mersenne_twister.random_double(size=3)-0.5)*0.2
    wells.append(r * site + t_noise)
  return wells
