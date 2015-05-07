#!/usr/bin/env python

import sys
import logging
import time

import util

from settings import session, api_url, tenant_url, public_interface

logging.info("using api_url = %s and tenant_url = %s" % (api_url, tenant_url))

step = util.step

#
#
step("Get a list of all instances currently in the system")
#     ===================================================
#


def instance_report():
    logging.info("Requesting a list of instances...")
    r = session.get(tenant_url + "/compute/instance/")
    util.check_response(r)

    instance_ids = r.json()

    logging.info("Found %d existing instances." % (len(instance_ids)))

    if len(instance_ids) > 0:
        t = []

        for id in instance_ids:
            logging.info("Requesting information for instance %s" % (id, ))

            # The instance ID refers to a collection.  Since we want to get a summary
            # of information about the collection, strip off the trailing slash.
            instance_url = tenant_url + "/compute/instance/" + id.rstrip("/")

            r = session.get(instance_url)
            util.check_response(r)
            info = r.json()

            name = "(unassigned)"
            r = session.get(instance_url + "/tag/name")
            if r.status_code == 200:
                name = r.json()

            ipv4_address = "(unassigned)"
            r = session.get(instance_url + "/network/" + public_interface + "/address")
            if r.status_code == 200:
                ipv4_address = r.json()["IPv4"]

            t.append((id, name, info["state"], ipv4_address, util.basename(info["size"]), util.basename(info["profile"])))

        print util.column_report("Instance Summary", 
                                 ("Id", "Name", "State", "IPv4 Address", "Size", "Profile"), t)
    else:
        print "No VM instances currently exist."
        print

instance_report()

util.end_step()

#
#
step("Request a listing of available VM profiles")
#     ==========================================
#

logging.info("Requesting a list of possible profiles...")
r = session.get(api_url + "/v0/compute/profile/")
util.check_response(r)

profile_ids = r.json()

if len(profile_ids) > 0:
    print util.column_report("Available VM Profiles",
                             ["Profile Id"], [[x] for x in r.json()])
else:
    print "No VM profiles found.  Unfortunately, we can't continue this API example."
    sys.exit(1)

util.end_step()


#
#
step("Request a listing of available VM sizes")
#     =======================================
#

logging.info("Requesting a list of possible VM sizes...")
r = session.get(api_url + "/v0/compute/size/")
util.check_response(r)

t = []
size_ids = r.json()
if len(size_ids) > 0:
    for id in size_ids:
        r = session.get(api_url + "/v0/compute/size/" + id.rstrip("/"))
        util.check_response(r)

        info = r.json()

        t.append([id, info["ncpu"], info["memory"]])


    print util.column_report("Available VM Sizes",
                             ["Id", "Number of CPUs", "Amount of RAM"],
                             t)
else:
    print "No VM sizes found.  Unfortunately, we can't continue this API example."
    sys.exit(1)

util.end_step()


#
#
step("Create some virtual machine instances")
#     =====================================
#

def create_vm(name, size, profile):
    logging.info("Creating new instance named '%s'" % (name))
    form = {
        "size": size,
        "profile": profile,
        "ssh-key": open("id_rsa.pub", "r")
    }

    r = session.post(tenant_url + "/compute/instance/", files=form)
    util.check_response(r, expected_statuses=[201])

    instance_uri = r.headers['location']

    info = r.json()
    logging.info("New instance located at '%s'." % (instance_uri))
    logging.debug(info)

    logging.info("Tagging instance with new name.")
    r = session.post(api_url + instance_uri + "/tag/", files=dict(name="name",
                                                                       value=name))
    util.check_response(r, expected_statuses=[201])

    return instance_uri


instance_uris = []

instance_uris.append(create_vm("New Developer Instance", size_ids[0], profile_ids[0]))
instance_uris.append(create_vm("Another Developer Instance", size_ids[0], profile_ids[0]))
instance_uris.append(create_vm("Yet Another Developer Instance", size_ids[0], profile_ids[0]))

instance_report()

util.end_step()


#
#
step("Start all of our new Virtual Machines")
#     =====================================
#

def control_vm(uri, action):
    logging.info("Running action '%s' at '%s'" % (action, uri))
    r = session.post(api_url + uri + "/" + action)
    # If the status code is 400, it means that the instance was already in that state.
    util.check_response(r, expected_statuses=[200, 400])

for uri in instance_uris:
    control_vm(uri, "start")

util.end_step()


#
#
step("Show Our Instance Status")
#     ========================
#

instance_report()

util.end_step()


#
#
step("Waiting (up to 180 seconds) For IPv4 Addresses To Be Assigned...")
#     =============================================================
#
logging.info("Waiting for all of our instances to be assigned IPv4 addresses...")

start = time.time()
addresses = [None] * len(instance_uris)

found = 0
while True:
    if (time.time() - start) > 180:
        logging.error("Timing out waiting for IPv4 addresses.")
        break

    for idx, uri in enumerate(instance_uris):
        if addresses[idx] != None:
            continue

        logging.info("Attempting to get the address for instance '%s'" % (uri,))
        uri = api_url + uri + "/network/" + public_interface + "/address"
        r = session.get(uri)
        if r.status_code != 200:
            continue

        addresses[idx] = r.json()["IPv4"]

        found += 1

    if found >= len(instance_uris):
        break

    logging.debug("Sleeping for 5 seconds...")
    time.sleep(5)

t = []

logging.info("got the following addresses %s" % (addresses,))

instance_report()

util.end_step()


#
#
step("Deleting all of the Virtual Machines We Created")
#     =============================================
#

def delete_vm(uri):
    control_vm(uri, "stop")

    logging.info("Deleting instance at '%s'" % (uri))
    r = session.delete(api_url + uri)
    util.check_response(r)


for uri in instance_uris:
    delete_vm(uri)

util.end_step()


#
#
step("Show Our Instance Status")
#     ========================
#

instance_report()
