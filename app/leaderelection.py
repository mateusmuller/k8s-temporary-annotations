import socket
from kubernetes import config
from kubernetes.leaderelection import leaderelection
from kubernetes.leaderelection.resourcelock.configmaplock import ConfigMapLock
from kubernetes.leaderelection import electionconfig

config.load_incluster_config()
candidate_id = socket.gethostname()
lock_name = "tmp-annotations-lock"
lock_namespace = "default"


def leader():
    print(f"I am leader")


config = electionconfig.Config(
    ConfigMapLock(lock_name, lock_namespace, candidate_id),
    lease_duration=17,
    renew_deadline=15,
    retry_period=5,
    onstarted_leading=leader,
    onstopped_leading=None,
)

leaderelection.LeaderElection(config).run()
