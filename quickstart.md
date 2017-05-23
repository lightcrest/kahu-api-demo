
Kahu Web Services Quickstart Guide
==================================

----

## Introduction


Kahu supports a rich set of APIs for direct use by programmers for both administration and automation.  These APIs are exposed as RESTful web services over HTTP, using JSON as the response format.  Arguments may be passed via query parameters, or as part of a form body, depending on the request.

Being a RESTful API, all of the described URIs support some number of HTTP verbs:

- `POST`

	Causes the creation of a new resource, or the execution of a specific operation.

- `GET`

	Returns the value of the resource, or collection requested.  In common use, this will be a JSON value.

- `DELETE`

	Causes a specific resource to be deleted.  Usually this operation is recursive.

- `PUT`

	Update the value of a resource.

This quickstart guide will enumerate the most commonly used API methods provided by Kahu, using `curl` as the HTTP client.  In these examples, extraneous headers have been removed.  Please note: authentication is not shown in these examples, and is dependent on the authentication model associated with the target Kahu deployment.

----

## Tenants

Kahu supports namespacing different groups of resources into 'tenants'.  These tenants are arbitrary and are created for reasons of access control, organization, et cetera.

Note: For the purpose of this document, examples are shown using an arbitrary tenant identifier.  For your specific use, you should use the tenant identifier provided to you.

----

## Loging Into A Role

In the case where native Kahu authentication is being used, it's required that you first authenticate with the cluster before being able to make API requests.  To do this, a `POST` request is made to create a new session:


        $ curl -i -X POST http://kahu/v0/auth/login -F role=joeuser -F password=picketfence
        HTTP/1.1 200 OK
        Set-Cookie: KAHU_SESSION_TOKEN=cm9sZTASDLKJALSKJJSJKKREDACTED; Path=/

        {"session":"6251ad1f-ca42-a69a-0a6d-b68bLOREMIPSUM","uri":"/v0/auth/role/joeuser"}

If login is successful, a `200` status will be the result, and one or more cookies will be returned.  In order to use the API for future requests, the returned cookies from the login operation must be passed in.

----

## Setting A Role Password

In order to change a role password, you must `POST` against the password endpoint:

       $ curl -i -b KAHU_SESSION_TOKEN=cm9sZTASDLKJALSKJJSJKKREDACTED -X POST http://kahu/v0/auth/password -F current-password=picketfence -F password=greengrass
       HTTP/1.1 200 OK

       "password set"

Note: The `KAHU_SESSION_TOKEN` cookie is being passed in, because it was provided as part of the login operation.

----

## Logging Out Of A Role's Session

In order to log out of a session, a `POST` against the logout endpoint must be done:

        $ curl -i -b KAHU_SESSION_TOKEN=cm9sZTASDLKJALSKJJSJKKREDACTED -X POST http://kahu/v0/auth/logout
        HTTP/1.1 200 OK
        Set-Cookie: KAHU_SESSION_TOKEN=NULL; Path=/kahu; Max-Age=0

        "logged out"

Note: The `KAHU_SESSION_TOKEN` must be passed in to log out.  It's a requirement that at this point the previously provided cookie value no longer be used, and the server's new `Set-Cookie` request be honored.

----

## Listing Available Profiles


Every virtual machine is based off of a 'profile'.  These profiles provide information, such as:

- Base filesystem image (e.g. which Linux distribution) to boot the virtual machine off of.
- The initial storage configuration (e.g. disk sizes, and extra storage attached).
- The initial networking configuration (e.g. which physical and virtual switches to connect network interfaces to).

To get a list of available profiles, a `GET` request is made:

	$ curl -i -X GET http://kahu/v0/compute/profile/
	HTTP/1.1 200
	Content-Type: application/json

	{
	  "debian-jessie-2016011200": {
	    "name": "debian-jessie-2016011200",
	    "network": {
	      "external": {
	        "type": "virtio"
	      }
	    },
	    "storage": {
	      "root": {
	        "bootable": true,
	        "bus": "",
	        "guest-iface": "virtio",
	        "media-type": "disk",
	        "order": 0,
	        "size": 16384,
	        "tag": null,
	        "type": "qcow2",
	        "vdi-name": "root_1452659256_0"
	      }
	    }
	  },
	  "empty": {
	    "network": {
	      "external": {
	        "type": "virtio"
	      }
	    },
	    "storage": {}
	  }
	}

----

## Listing Available VM Sizes


Inside Kahu, each virtual machine has a specified size.  This size dictates virtual machine features like the amount of RAM, and the number of virtual CPUs.  To obtain the virtual machine sizes provided by the system, simply make a `GET` request:

	$ curl -i -X GET http://kahu/v0/compute/size/
	HTTP/1.1 200
	Content-Type: application/json

	{
	  "1cpu256mb": {
	    "memory": 256,
	    "ncpu": 1
	  }
	}

----

## Creating Instances


One of the most common Kahu operations is creating a virtual machine instance.  In order to do this, one sends a `POST` request with the following form parameters:

- profile - **required**

	The template or 'profile' to base this new virtual machine off of.  These profiles are pre-configured.

- size - **required**

	The size of the virtual machine to create.  This size refers to a pre-configured virtual machine size.

- hypervisor - **required**

	Which hypervisor this instance should be launched on (e.g. /v0/hypervisor/instance/0).

- ssh-key - **optional**

	The SSH public key to pre-seed the virtual machine with.  By default, Kahu assigns this key to the ```admin``` user, which also may ```sudo``` as ```root```.

The response consists of:

- Location

	This header contains the URI for the newly created instance.  All operations made against a specific VM are made via this return URI.

- A JSON body

	This includes the arguments used for image creation.

An example of creating a new virtual machine instance would be the following:

	$ curl -i http://kahu/v0/compute/instance/ -X POST -F profile=debian-jessie-amd64 -F size=1cpu256mb -F ssh-key=@id_rsa.pub
	HTTP/1.1 201
	Content-Type: application/json
	Location: /v0/compute/instance/0/

	{
		"message": "instance created",
		"profile": "/v0/compute/profile/debian-jessie/",
		"size": "/v0/compute/size/1cpu256meg/",
		"ssh-key": "ssh-rsa AAAAB[...]Tz5abf"
	}

NOTE: If the profile you're creating the instance from does not have ```cloud-init``` installed, ```ssh-key``` will be ignored.

----

## Attaching additional storage to a VM


In order to attach a new storage image to a virtual machine, one uses the VM URI returned by the `Location` header when the VM was created (e.g. `/v0/tenant/0/compute/instance/0/`).  For instance, to create a 16 GB volume attached to our new VM:

	$ curl -i http://kahu/v0/compute/instance/0/storage/ -X POST -F name=newvol -F size=16384
	HTTP/1.1 201
	Content-Type: application/json
	Location: /v0/compute/instance/0/storage/newvol/

	{
		"name": "newvol",
                "size": 16384
	}

The `Location` header lists the URI that can be used to perform actions on the volume.

In addition to the options shown in the above example, it's possible to set additional flags on the storage volume:

- ```bootable``` may be set to ```true``` or ```false```.
- ```file``` is a ```raw``` or ```QCOW2``` image to use as the storage volume.  These are the only two file formats supported.
- ```media-type``` (e.g. disk, cdrom)
- ```guest-iface``` (e.g. virtio, ide, scsi, usb)
- ```type``` (e.g. qcow2, raw)

**NOTE**: ```file``` and ```size``` are mutually exclusive.

----

## Listing storage attached to a VM


To obtain a list of all storage volumes attached to a VM, a `GET` request can be made against the VM's storage URI:

	$ curl -i http://kahu/v0/tenant/0/compute/instance/0/storage/
	HTTP/1.1 200
	Content-Type: application/json

	{
	  "root": {
	    "bootable": true,
	    "bus": "",
	    "guest-iface": "virtio",
	    "media-type": "disk",
	    "order": 0,
	    "size": 16384,
	    "tag": null,
	    "type": "qcow2",
	    "vdi-name": "root_1452659256_0"
	  },
	  "config": {
	    "bootable": false,
	    "bus": "",
	    "guest-iface": "ide",
	    "media-type": "disk",
	    "order": 1,
	    "size": 1,
	    "tag": null,
	    "type": "qcow2",
	    "vdi-name": "config_1453356364_0"
	  },
	  "newvol": {
	    "bootable": false,
	    "bus": "",
	    "guest-iface": "virtio",
	    "media-type": "disk",
	    "name": "newvol",
	    "order": 2,
	    "size": 16384,
	    "tag": null,
	    "type": "qcow2",
	    "vdi-name": "newvol_1453356430_0"
	  }
	}

The three volumes that are attached:

- root

	The root filesystem attached to the virtual machine.

- config

	The configuration volume provided to **cloud-init** for installing the initial SSH key, and providing instance meta-data.

- newvol

	The new volume we just created.

----

## Listing storage volume details.


To obtain the details of the volume we just attached, it's possible to query the volume directly with a `GET` request:

	$ curl -i http://kahu/v0/tenant/0/compute/instance/0/storage/newvol
	HTTP/1.1 200
	Content-Type: application/json

	{
	  "bootable": false,
	  "guest-iface": "virtio",
	  "media-type": "disk",
	  "name": "newvol",
	  "order": 2,
	  "size": 16384,
	  "type": "qcow2",
	  "vdi-name": "newvol_1453356430_0"
	}

----

## Starting an instance.


Starting an existing VM is as simple as sending a `POST` request to a URI off of the VM:


	$ curl -i http://kahu/v0/compute/instance/0/start -X POST
	HTTP/1.1 200
	Content-Type: application/json

	{
		"message": "instance started"
	}


The body of the response includes a message related to the starting of the instance.  The `Status` header returning `200` is the authoritative response that the instance was started.

----

## Obtaining an instance's IP address.

After an instance is started, and has obtained its network configuration via DHCP, it is possible to retrieve the instance's IP address information using a `GET` request:

    $ curl -i http://kahu/v0/compute/instance/0/network/default/address
    HTTP/1.1 200
    Content-Type: application/json

    {
    	"IPv4": "256.303.400.71"
    }

This is the `IPv4` address assigned to the instance's `default` network interface.  Note: if the instance has not been assigned an IP address via DHCP, a `Status` of `404` will be returned.

----

## Creating a new snapshot.


Kahu supports the creation of VM snapshots.  In order to make a VM snapshot, a `POST` request is made against the VM's `snapshot` URI:

	$ curl -i http://kahu/v0/compute/instance/0/snapshot/ -X POST -F name=mysnapshot-2014-12-22
	HTTP/1.1 200
	Content-Type: application/json
	Location: /v0/compute/instance/0/snapshot/mysnapshot-2014-12-22/

The URI of the new snapshot is returned in the `Location` header.  This URI can be used to query information regarding the snapshot.

----

## Stopping an instance.


Stopping an existing VM is as simple as sending a `POST` request to a URI off of the VM:

	$ curl -i http://kahu/v0/compute/instance/0/stop -X POST
	HTTP/1.1 200
	Content-Type: application/json

	{
		"message": "instance stopped"
	}

The `Status` header returning `200` is the authoritative response that the instance was stopped.

----

## Deleting a volume.


To delete a volume off of a VM, a `DELETE` request is made against the volume's URI.

	$ curl -i http://kahu/v0/compute/instance/0/storage/newvol/ -X DELETE
	HTTP/1.1 200
	Content-Type: application/json

----

## Listing snapshot details.

It's possible to query the contents of a snapshot with a `GET` requests:

	$ curl -i http://kahu/v0/compute/instance/0/snapshot/mysnapshot-2014-12-22
	HTTP/1.1 200
	Content-Type: application/json

        {
            "network": ... ,
            "profile": "/v0/compute/profile/debian-jessie/",
	    "size": "/v0/compute/size/1cpu256meg/",
            "storage": ... ,
            "timestamp":"2016-01-21T21:03:32.243323149-08:00"}

        }



----

## Configuring Virtual-Hardware Quirks

Virtual machines can have several virtual hardware configuration options set on them, currently the following are supported:

- Microsoft HyperV Compatibility Mode (boolean flag)

These options may be set on existing stopped instances, using a `PUT` request.  An example of setting a hardware quirk:

	$ curl -i http://kahu/v0/compute/instance/0/hw/ -X PUT -F hyperv-compat=true
	HTTP/1.1 200
	Content-Type: application/json

	{
	        "message":"instance updated"
	}

----


## Deleting a VM instance.

In order to delete a virtual machine, it must be in a `stopped` state.  To perform the actual delete operation, a `DELETE` request is made:

	$ curl -i http://kahu/v0/tenant/0/compute/instance/0/ -X DELETE
	HTTP/1.1 200
	Content-Type: application/json

	{
		"message": "instance deleted"
	}

The server returning a `Status` of `200` is the authoritative response that the instance was deleted.  The JSON body may also include a message explaining the result.

----

## Conclusion

This document has served as a quickstart guide for using the Kahu REST APIs to manage virtual machines.  It is not a complete reference, but includes the most commonly used operations in an easy to understand format.
