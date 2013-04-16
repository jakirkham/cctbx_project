from __future__ import division

if __name__ == "__main__":
  import argparse
  import pickle

  parser = argparse.ArgumentParser(
    description = "Server process handling far end of remote execution",
    usage = "%(prog)s job-factory queue-factory (do not run directly!)",
    )
  parser.add_argument(
    "job",
    help = "Job factory pickle string",
    )
  parser.add_argument(
    "queue",
    help = "Job factory pickle string",
    )
  parser.add_argument( "--folder", default = ".", help = "Process workdir" )
  parser.add_argument(
    "--polltime",
    type = int,
    default = 0.01,
    help = "Poll intervall",
    )

  params = parser.parse_args()

  import os
  import sys
  os.chdir( params.folder )
  sys.path.append( os.path.abspath( params.folder ) )

  jfact = pickle.loads( params.job.decode( "string-escape" ) )
  qfact = pickle.loads( params.queue.decode( "string-escape" ) )

  from libtbx.queuing_system_utils import scheduling

  manager = scheduling.Scheduler(
    handler = scheduling.Unlimited(
      factory = lambda:
        scheduling.ExecutionUnit(
          factory = jfact,
          processor = scheduling.RetrieveProcessor( queue = qfact(), timeout = 1 ),
          ),
      ),
    polling_interval = params.polltime,
    )

  from libtbx.queuing_system_utils import remote

  server = remote.SchedulerServer(
    instream = sys.stdin,
    outstream = sys.stdout,
    manager = manager,
    )

  # Redirect standard filehandles, so that the communication stream is intact
  from libtbx import utils
  sys.stdout = utils.null_out()

  server.serve()

