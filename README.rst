owimetadatabase_soilapi
==========================

``owimetadatabase`` is a semi-structured database application used for storage of geotechnical and structural data
on offshore wind turbine structures. 

The application allow parametric retrieval of data through an Application Programming Interface (API).

This repository provides basic examples of accessing data through the API using a Python package which hides the complexity of preparing HTTP requests and parsing JSON responses.

The database application is described in an <a href="https://link.springer.com/article/10.1007/s11440-022-01551-3">Open Access journal paper</a> in the journal Acta Geotechnica.

Example of data retrieval are provided in the ``notebooks`` subdirectory, which contains Jupyter notebooks with example of data retrieval. A concise workflow with the Python package ``owimetadatabase_soilapi`` is explained.

Data sources
-------------------------

Geotechnical data from the Dutch <a href="https://offshorewind.rvo.nl/">RVO sites</a> is shared under a Creative Commons licence (4.0 CC BY). 

Geotechnical data from three <a href="https://pinta.bsh.de/?lang=en">BSH sites</a> in Germany is also shared.

Crown Estate offshore wind farm data is shared from <a href="https://www.marinedataexchange.co.uk/search?searchQuery=geotechnical">Marine Data Exchange</a>.

Public-domain data on offshore wind turbine locations and detailed monopile geometry is not available.

Obtaining access
-------------------

In order to access the data, you need to have an account and an associated API token. Contact us to obtain access (bruno.stuyts@vub.be).

Installation
---------------

``pip install .``

License and copyright
-----------------------

This work is provided under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. Please check the license terms below and in the license file.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

  Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

  Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

  Neither the name of the software nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
  
<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.

Copyright (c) 2017-2021, OWI-lab, All rights reserved.

Disclaimer
-------------

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.