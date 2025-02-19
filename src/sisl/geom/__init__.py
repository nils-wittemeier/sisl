# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
Common geometries
=================

Bulk
====

   sc
   bcc
   fcc
   rocksalt
   hcp
   diamond


Surfaces
========

   fcc_slab
   bcc_slab
   rocksalt_slab


1D materials
============

   nanoribbon
   graphene_nanoribbon
   agnr
   zgnr
   nanotube


2D materials
============

   honeycomb
   bilayer
   graphene

"""
from ._category import *
from ._composite import *
from ._neighbors import *
from .basic import *
from .bilayer import *
from .flat import *
from .nanoribbon import *
from .nanotube import *
from .special import *
from .surfaces import *
