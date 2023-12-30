
//    --------------------------------------------------------------------
//
//    This file is part of Luna.
//
//    LUNA is free software: you can redistribute it and/or modify
//    it under the terms of the GNU General Public License as published by
//    the Free Software Foundation, either version 3 of the License, or
//    (at your option) any later version.
//
//    Luna is distributed in the hope that it will be useful,
//    but WITHOUT ANY WARRANTY; without even the implied warranty of
//    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//    GNU General Public License for more details.
//
//    You should have received a copy of the GNU General Public License
//    along with Luna. If not, see <http://www.gnu.org/licenses/>.
//
//    Please see LICENSE.txt for more details.
//
//    --------------------------------------------------------------------

#include <pybind11/pybind11.h>
#include <pybind11/stl.h> 
#include <pybind11/eigen.h>

#include "luna.h"

class lunapi_init_t 
{
public:
    lunapi_init_t() 
    {
      // initialize the library
      lunapi_t::init();
      std::cout << "luna/lunapi v0.1 (30-Dec-2023)\n";      
    }

    // ~lunapi_init_t()
    // {
    //     //finalize 
    // }
};


namespace py = pybind11;

PYBIND11_MODULE(lunapi, m) {

  // ensure lunapi_t::init() is called at start up
  static lunapi_init_t lunapi_init;
  
  m.doc() = "LunaAPI : Python bindings to the C/C++ Luna library";         

  m.def("init", &lunapi_t::init, "Initiate the Luna library" );
    
  py::class_<lunapi_t>(m, "new")
    .def(py::init<const std::string &>())
    .def( "attach_edf",&lunapi_t::attach_edf,"Attach an EDF" )
    .def( "attach_annot",&lunapi_t::attach_annot,"Attach an annotation file to the current EDF" )
    
    .def( "refresh", &lunapi_t::refresh,"Reattach the current EDF")
    .def( "drop", &lunapi_t::refresh,"Drop the current EDF" )
    .def( "clear" , &lunapi_t::clear,"Clear all variables" )

    .def( "channels", &lunapi_t::channels,"Return a list of channel labels" )
    .def( "annots", &lunapi_t::annots,"Return a list of annotation class labels" )
    .def( "stat" , &lunapi_t::status,"Return a map/dict of key details on the current EDF" )

    .def( "e2i" , &lunapi_t::epochs2intervals , "Convert epoch numbers to interval tuples" )
    .def( "s2i" , &lunapi_t::seconds2intervals , "Convert second (start/stop tuples) to interval tuples" )
        
    .def( "slice",&lunapi_t::slice,"Return a data matrix/column header tuple" )
    .def( "slices",&lunapi_t::slices,"Return a list of data matrices (one per epoch/interval)" )

    .def_static("var",py::overload_cast<const std::string &,const std::string &>(&lunapi_t::var),"Set a variable value")
    .def_static("var",py::overload_cast<const std::string &>(&lunapi_t::var),"Show a variable value")
    .def_static("vars",&lunapi_t::vars,"List several variables")
    .def_static("dropvar",&lunapi_t::dropvar,"Drop a variable")
    .def_static("dropvars",&lunapi_t::dropvars,"Drop several variables")
   
    .def("eval",&lunapi_t::eval,"Evaluate an arbitrary set of Luna commands given an attacged EDF" )
    .def("commands",&lunapi_t::commands,"List commands resulting from a prior eval()" )
    .def("strata",&lunapi_t::strata,"List command/strata tuples resulting from a prior eval()" )
    .def("variables",&lunapi_t::variables,"List variables (columns) from a table (defined by a command/strat pair) from a prior eval()")
    .def("data",&lunapi_t::data , "Return table (defined by a command/strata pair) from a prior eval()" )
    
    .def("__repr__",[](const lunapi_t & a) { return "<lunapi-instance>"; });

    
}

