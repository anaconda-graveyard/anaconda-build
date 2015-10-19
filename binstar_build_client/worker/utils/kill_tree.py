
import psutil
import logging


log = logging.getLogger('binstar.build')

def kill_tree(p0):
    'Kill all processes and child processes'
    try:
        log.warning("Kill Tree parent pid:%s" % p0.pid)
        parent = psutil.Process(p0.pid)
    except psutil.NoSuchProcess:
        log.warning("Parent pid %s is already dead" % p0.pid)
        # Already dead
        return

    children = parent.children(recursive=True)

    p0.kill()
    for child in children:
        if child.is_running():
            log.warning(" - Kill child pid %s" % child.pid)
            child.kill()
