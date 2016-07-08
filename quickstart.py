#!/usr/bin/env python

import sys
import logging
import time
from urlparse import urljoin

import util

from settings import session, api_url, tenant_url, public_interface, wait_for_addresses, size_id, profile_id, hypervisor_id

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
            if info["name"]:
                name = info["name"]

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

def create_vm(name, size, profile, hypervisor):
    logging.info("Creating new instance named '%s'" % (name))
    form = {
        "size": size,
        "profile": profile,
        "ssh-key": open("id_rsa.pub", "r"),
        "name": name,
        "hypervisor": hypervisor
    }

    r = session.post(tenant_url + "/compute/instance/", files=form)
    util.check_response(r, expected_statuses=[201])

    instance_url = urljoin(api_url, r.headers['location'])
    info = r.json()
    logging.info("New instance located at '%s'." % (instance_url))
    logging.debug(info)

    return instance_url


instance_urls = []

if not size_id:
    if len(size_ids) < 1:
        raise ValueError("no sizes available from server")

    if type(size_ids) is dict:
        k = size_ids.keys()
        size_id = k[0]
    elif type(size_ids) is list:
        size_id = size_ids[0]
    else:
        raise TypeError("unknown size_id type")

if not profile_id:
    if len(profile_ids) < 1:
        raise ValueError("no profiles available from server")

    if type(profile_ids) is dict:
        k = profile_ids.keys()
        profile_id = k[0]
    elif type(profile_ids) is list:
        profile_id = profile_id[0]
    else:
        raise TypeError("unknown profile_id type")

instance_urls.append(create_vm("New Developer Instance", size_id, profile_id, hypervisor_id))
instance_urls.append(create_vm("Another Developer Instance", size_id, profile_id, hypervisor_id))
instance_urls.append(create_vm("Yet Another Developer Instance", size_id, profile_id, hypervisor_id))

instance_report()

util.end_step()


#
#
step("Start all of our new Virtual Machines")
#     =====================================
#

def control_vm(url, action):
    logging.info("Running action '%s' at '%s'" % (action, url))
    r = session.post(url + "/" + action)
    # If the status code is 400, it means that the instance was already in that state.
    util.check_response(r, expected_statuses=[200, 400])

for url in instance_urls:
    control_vm(url, "start")

util.end_step()


#
#
step("Show Our Instance Status")
#     ========================
#

instance_report()

util.end_step()



if wait_for_addresses:
    #
    #
    step("Waiting (up to 180 seconds) For IPv4 Addresses To Be Assigned...")
    #     =============================================================
    #
    logging.info("Waiting for all of our instances to be assigned IPv4 addresses...")

    start = time.time()
    addresses = [None] * len(instance_urls)

    found = 0
    while True:
        if (time.time() - start) > 180:
            logging.error("Timing out waiting for IPv4 addresses.")
            break

        for idx, url in enumerate(instance_urls):
            if addresses[idx] != None:
                continue

            logging.info("Attempting to get the address for instance '%s'" % (url,))
            url = url + "/network/" + public_interface + "/address"
            r = session.get(url)
            if r.status_code != 200:
                continue

            addresses[idx] = r.json()["IPv4"]

            found += 1

        if found >= len(instance_urls):
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
    control_vm(url, "stop")

    logging.info("Deleting instance at '%s'" % (uri))
    r = session.delete(url)
    util.check_response(r)


for url in instance_urls:
    delete_vm(url)

util.end_step()


#
#
step("Show Our Instance Status")
#     ========================
#

instance_report()
