from __future__ import generators
from libtbx.option_parser import option_parser
from libtbx.utils import Sorry
from libtbx import easy_run
from libtbx import introspection
import difflib
from stdlib import math
import sys, os

try:
  import threading
except ImportError:
  threading = None
else:
  import Queue

diff_function = getattr(difflib, "unified_diff", difflib.ndiff)

Exception_expected = RuntimeError("Exception expected.")

class Default: pass

def run_tests(build_dir, dist_dir, tst_list):
  args = [arg.lower() for arg in sys.argv[1:]]
  command_line = (option_parser(
    usage="run_tests [-j n]",
    description="Run several threads in parallel, each picking and then"
                " running tests one at a time.")
    .option("-j", "--threads",
      action="store",
      type="int",
      default=1,
      help="number of threads",
      metavar="INT")
    .option("-v", "--verbose",
      action="store_true",
      default=False)
    .option("-q", "--quick",
      action="store_true",
      default=False)
    .option("-g", "--valgrind",
      action="store_true",
      default=False)
  ).process(args=args, max_nargs=0)
  co = command_line.options
  if (threading is None or co.threads == 1):
    for cmd in iter_tests_cmd(co, build_dir, dist_dir, tst_list):
      print cmd
      sys.stdout.flush()
      easy_run.call(command=cmd)
      print
      sys.stderr.flush()
      sys.stdout.flush()
  else:
    cmd_queue = Queue.Queue()
    for cmd in iter_tests_cmd(co, build_dir, dist_dir, tst_list):
      cmd_queue.put(cmd)
    threads_pool = []
    log_queue = Queue.Queue()
    interrupted = threading.Event()
    for i in xrange(co.threads):
      working_dir = os.tempnam()
      os.mkdir(working_dir)
      t = threading.Thread(
        target=make_pick_and_run_tests(working_dir, interrupted,
                                       cmd_queue, log_queue))
      threads_pool.append(t)
    for t in threads_pool:
      t.start()
    finished_threads = 0
    while(1):
      try:
        log = log_queue.get()
        if isinstance(log, tuple):
          msg = log[0]
          print >> sys.stderr, "\n +++ thread %s +++\n" % msg
          finished_threads += 1
          if finished_threads == co.threads: break
        else:
          print log
      except KeyboardInterrupt:
        print
        print "********************************************"
        print "** Received Keyboard Interrupt            **"
        print "** Waiting for running tests to terminate **"
        print "********************************************"
        interrupted.set()
        break

def make_pick_and_run_tests(working_dir, interrupted,
                            cmd_queue, log_queue):
  def func():
    while(not interrupted.isSet()):
      try:
        cmd = cmd_queue.get(block=True, timeout=0.2)
        log = "\n%s\n" % cmd
        proc = easy_run.subprocess.Popen(cmd,
                                  shell=True,
                                  stdout=easy_run.subprocess.PIPE,
                                  stderr=easy_run.subprocess.STDOUT,
                                  cwd=working_dir)
        proc.wait()
        log += "\n%s" % proc.stdout.read()
        log_queue.put(log)
      except Queue.Empty:
        log_queue.put( ("done",) )
        break
      except KeyboardInterrupt:
        break
  return func

def iter_tests_cmd(co, build_dir, dist_dir, tst_list):
  if (os.name == "nt"):
    python_exe = sys.executable
  else:
    python_exe = "libtbx.python"
  for tst in tst_list:
    cmd_args = ""
    if (type(tst) == type([])):
      if (co.verbose):
        cmd_args = " " + " ".join(["--Verbose"] + tst[1:])
      elif (co.quick):
        cmd_args = " " + " ".join(tst[1:])
      tst = tst[0]
    elif (co.verbose):
      continue
    if (tst.startswith("$B")):
      tst_path = tst.replace("$B", build_dir)
    else:
      tst_path = tst.replace("$D", dist_dir)
    assert tst_path.find("$") < 0
    tst_path = os.path.normpath(tst_path)
    cmd = ""
    if (tst_path.endswith(".py")):
      if (co.valgrind):
        cmd = "libtbx.valgrind "
      cmd += python_exe + " " + tst_path
    else:
      if (co.valgrind):
        cmd = os.environ["LIBTBX_VALGRIND"] + " "
      cmd += tst_path
    cmd += cmd_args
    yield cmd

def approx_equal_core(a1, a2, eps, multiplier, out, prefix):
  if hasattr(a1, "__len__"): # traverse list
    assert len(a1) == len(a2)
    for i in xrange(len(a1)):
      if not approx_equal_core(
                a1[i], a2[i], eps, multiplier, out, prefix+"  "):
        return False
    return True
  is_complex_1 = isinstance(a1, complex)
  is_complex_2 = isinstance(a2, complex)
  if (is_complex_1 and is_complex_2): # complex & complex
    if not approx_equal_core(
              a1.real, a2.real, eps, multiplier, out, prefix+"real "):
      return False
    if not approx_equal_core(
              a1.imag, a2.imag, eps, multiplier, out, prefix+"imag "):
      return False
    return True
  elif (is_complex_1): # complex & number
    if not approx_equal_core(
              a1.real, a2, eps, multiplier, out, prefix+"real "):
      return False
    if not approx_equal_core(
              a1.imag, 0, eps, multiplier, out, prefix+"imag "):
      return False
    return True
  elif (is_complex_2): # number & complex
    if not approx_equal_core(
              a1, a2.real, eps, multiplier, out, prefix+"real "):
      return False
    if not approx_equal_core(
              0, a2.imag, eps, multiplier, out, prefix+"imag "):
      return False
    return True
  ok = True
  d = a1 - a2
  if (abs(d) > eps):
    if (multiplier is None):
      ok = False
    else:
      am = max(a1,a2) * multiplier
      d = (am - d) - am
      if (d != 0):
        ok = False
  if (out is not None):
    annotation = ""
    if (not ok):
      annotation = " approx_equal ERROR"
    print >> out, prefix + str(a1) + annotation
    print >> out, prefix + str(a2) + annotation
    print >> out, prefix.rstrip()
    return True
  return ok

def approx_equal(a1, a2, eps=1.e-6, multiplier=1.e10, out=Default, prefix=""):
  ok = approx_equal_core(a1, a2, eps, multiplier, None, prefix)
  if (not ok and out is not None):
    if (out is Default): out = sys.stdout
    print >> out, prefix + "approx_equal eps:", eps
    print >> out, prefix + "approx_equal multiplier:", multiplier
    assert approx_equal_core(a1, a2, eps, multiplier, out, prefix)
  return ok

def not_approx_equal(a1, a2, eps=1.e-6, multiplier=1.e10):
  return not approx_equal(a1, a2, eps, multiplier, out=None)

def eps_eq_core(a1, a2, eps, out, prefix):
  if (hasattr(a1, "__len__")): # traverse list
    assert len(a1) == len(a2)
    for i in xrange(len(a1)):
      if (not eps_eq_core(a1[i], a2[i], eps, out, prefix+"  ")):
        return False
    return True
  if (isinstance(a1, complex)): # complex numbers
    if (not eps_eq_core(a1.real, a2.real, eps, out, prefix+"real ")):
      return False
    if (not eps_eq_core(a1.imag, a2.imag, eps, out, prefix+"imag ")):
      return False
    return True
  ok = True
  if (a1 == 0 or a2 == 0):
    if (abs(a1-a2) > eps):
      ok = False
  else:
    l1 = round(math.log(abs(a1)))
    l2 = round(math.log(abs(a2)))
    m = math.exp(-max(l1, l2))
    if (abs(a1*m-a2*m) > eps):
      ok = False
  if (out is not None):
    annotation = ""
    if (not ok):
      annotation = " eps_eq ERROR"
    print >> out, prefix + str(a1) + annotation
    print >> out, prefix + str(a2) + annotation
    print >> out, prefix.rstrip()
    return True
  return ok

def eps_eq(a1, a2, eps=1.e-6, out=Default, prefix=""):
  ok = eps_eq_core(a1, a2, eps, None, prefix)
  if (not ok and out is not None):
    if (out is Default): out = sys.stdout
    print >> out, prefix + "eps_eq eps:", eps
    assert eps_eq_core(a1, a2, eps, out, prefix)
  return ok

def not_eps_eq(a1, a2, eps=1.e-6):
  return not eps_eq(a1, a2, eps, None)

def is_below_limit(
      value,
      limit,
      eps=1.e-6,
      info_low_eps=None,
      out=Default,
      info_prefix="INFO LOW VALUE: "):
  if (isinstance(value, (int, float)) and value < limit + eps):
    if (info_low_eps is not None and value < limit - info_low_eps):
      if (out is not None):
        if (out is Default): out = sys.stdout
        introspection.show_stack(
          frames_back=1, reverse=True, out=out, prefix=info_prefix)
        print >> out, \
          "%sis_below_limit(value=%s, limit=%s, info_low_eps=%s)" % (
            info_prefix, str(value), str(limit), str(info_low_eps))
    return True
  if (out is not None):
    if (out is Default): out = sys.stdout
    print >> out, "ERROR:", \
      "is_below_limit(value=%s, limit=%s, eps=%s)" % (
        str(value), str(limit), str(eps))
  return False

def is_above_limit(
      value,
      limit,
      eps=1.e-6,
      info_high_eps=None,
      out=Default,
      info_prefix="INFO HIGH VALUE: "):
  if (isinstance(value, (int, float)) and value > limit - eps):
    if (info_high_eps is not None and value > limit + info_high_eps):
      if (out is not None):
        if (out is Default): out = sys.stdout
        introspection.show_stack(
          frames_back=1, reverse=True, out=out, prefix=info_prefix)
        print >> out, \
          "%sis_above_limit(value=%s, limit=%s, info_high_eps=%s)" % (
            info_prefix, str(value), str(limit), str(info_high_eps))
    return True
  if (out is not None):
    if (out is Default): out = sys.stdout
    print >> out, "ERROR:", \
      "is_above_limit(value=%s, limit=%s, eps=%s)" % (
        str(value), str(limit), str(eps))
  return False

def show_diff(a, b, selections=None, expected_number_of_lines=None):
  if (selections is None):
    assert expected_number_of_lines is None
  else:
    a_lines = a.splitlines(1)
    a = []
    for selection in selections:
      for i in selection:
        if (i < 0): i += len(a_lines)
        a.append(a_lines[i])
      a.append("...\n")
    a = "".join(a[:-1])
  if (a != b):
    print "".join(diff_function(b.splitlines(1), a.splitlines(1)))
    return True
  if (    expected_number_of_lines is not None
      and len(a_lines) != expected_number_of_lines):
    print \
      "show_diff: expected_number_of_lines != len(a.splitlines()): %d != %d" \
        % (expected_number_of_lines, len(a_lines))
    return True
  return False

class RunCommandError(Sorry): pass

def run_command(command, verbose=0):
  assert verbose >= 0
  if (verbose > 0):
    print command
    print
  result = easy_run.fully_buffered(command=command)
  if (len(result.stderr_lines) != 0):
    if (verbose == 0):
      print command
      print
    print "\n".join(result.stdout_lines)
    result.raise_if_errors()
  else:
    for line in result.stdout_lines:
      if (line == "Traceback (most recent call last):"):
        if (verbose == 0):
          print command
          print
        print "\n".join(result.stdout_lines)
        print
        raise RunCommandError("Traceback detected in output.")
  if (verbose > 1):
    print "\n".join(result.stdout_lines)
    print
  return result

def exercise():
  from cStringIO import StringIO
  assert approx_equal(1, 1)
  out = StringIO()
  assert not approx_equal(1, 0, out=out)
  assert not show_diff(out.getvalue().replace("1e-006", "1e-06"), """\
approx_equal eps: 1e-06
approx_equal multiplier: 10000000000.0
1 approx_equal ERROR
0 approx_equal ERROR

""")
  out = StringIO()
  assert not approx_equal(1, 2, out=out)
  assert not show_diff(out.getvalue().replace("1e-006", "1e-06"), """\
approx_equal eps: 1e-06
approx_equal multiplier: 10000000000.0
1 approx_equal ERROR
2 approx_equal ERROR

""")
  out = StringIO()
  assert not approx_equal(1, 1+1.e-5, out=out)
  assert approx_equal(1, 1+1.e-6)
  out = StringIO()
  assert not approx_equal(0, 1.e-5, out=out)
  assert approx_equal(0, 1.e-6)
  out = StringIO()
  assert not approx_equal([[0,1],[2j,3]],[[0,1],[-2j,3]], out=out, prefix="$%")
  assert not show_diff(out.getvalue().replace("1e-006", "1e-06"), """\
$%approx_equal eps: 1e-06
$%approx_equal multiplier: 10000000000.0
$%    0
$%    0
$%
$%    1
$%    1
$%
$%    real 0.0
$%    real 0.0
$%    real
$%    imag 2.0 approx_equal ERROR
$%    imag -2.0 approx_equal ERROR
$%    imag
$%    3
$%    3
$%
""")
  assert eps_eq(1, 1)
  out = StringIO()
  assert not eps_eq(1, 0, out=out)
  assert not show_diff(out.getvalue().replace("1e-006", "1e-06"), """\
eps_eq eps: 1e-06
1 eps_eq ERROR
0 eps_eq ERROR

""")
  out = StringIO()
  assert not eps_eq(1, 2, out=out)
  assert not show_diff(out.getvalue().replace("1e-006", "1e-06"), """\
eps_eq eps: 1e-06
1 eps_eq ERROR
2 eps_eq ERROR

""")
  out = StringIO()
  assert not eps_eq(1, 1+1.e-5, out=out)
  assert eps_eq(1, 1+1.e-6)
  out = StringIO()
  assert not eps_eq(0, 1.e-5, out=out)
  assert eps_eq(0, 1.e-6)
  out = StringIO()
  assert not eps_eq([[0,1],[2j,3]],[[0,1],[-2j,3]], out=out, prefix="$%")
  assert not show_diff(out.getvalue().replace("1e-006", "1e-06"), """\
$%eps_eq eps: 1e-06
$%    0
$%    0
$%
$%    1
$%    1
$%
$%    real 0.0
$%    real 0.0
$%    real
$%    imag 2.0 eps_eq ERROR
$%    imag -2.0 eps_eq ERROR
$%    imag
$%    3
$%    3
$%
""")
  assert is_below_limit(value=5, limit=10, eps=2)
  out = StringIO()
  assert is_below_limit(value=5, limit=10, eps=2, info_low_eps=1, out=out)
  assert not show_diff(out.getvalue(), """\
INFO LOW VALUE: is_below_limit(value=5, limit=10, info_low_eps=1)
""", selections=[[-1]], expected_number_of_lines=3)
  out = StringIO()
  assert not is_below_limit(value=15, limit=10, eps=2, out=out)
  assert not show_diff(out.getvalue(), """\
ERROR: is_below_limit(value=15, limit=10, eps=2)
""")
  out = StringIO()
  assert not is_below_limit(value=None, limit=3, eps=1, out=out)
  assert not is_below_limit(value=None, limit=-3, eps=1, out=out)
  assert not show_diff(out.getvalue(), """\
ERROR: is_below_limit(value=None, limit=3, eps=1)
ERROR: is_below_limit(value=None, limit=-3, eps=1)
""")
  assert is_above_limit(value=10, limit=5, eps=2)
  out = StringIO()
  assert is_above_limit(value=10, limit=5, eps=2, info_high_eps=1, out=out)
  assert not show_diff(out.getvalue(), """\
INFO HIGH VALUE: is_above_limit(value=10, limit=5, info_high_eps=1)
""", selections=[[-1]], expected_number_of_lines=3)
  out = StringIO()
  assert not is_above_limit(value=10, limit=15, eps=2, out=out)
  assert not show_diff(out.getvalue(), """\
ERROR: is_above_limit(value=10, limit=15, eps=2)
""")
  out = StringIO()
  assert not is_above_limit(value=None, limit=-3, eps=1, out=out)
  assert not is_above_limit(value=None, limit=3, eps=1, out=out)
  assert not show_diff(out.getvalue(), """\
ERROR: is_above_limit(value=None, limit=-3, eps=1)
ERROR: is_above_limit(value=None, limit=3, eps=1)
""")
  print "OK"

if (__name__ == "__main__"):
  exercise()
