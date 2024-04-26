
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

namespace py = pybind11;
using namespace pybind11::literals;

PYBIND11_MODULE(lunapi0, m) {

  m.doc() = "LunaAPI: Python bindings for the Luna C/C++ library";
  
  m.def( "inaugurate",
	 &lunapi_t::inaugurate,
	 py::return_value_policy::reference ,
	 "Start/return a reference to the Luna engine" );

  m.def( "retire",
	 &lunapi_t::retire,	 
	 "Retire an extant Luna engine" );

  m.def( "cmdfile" ,
	 &lunapi_t::cmdfile ,
	 "Load a Luna script from a file" );    

  m.def( "version" ,
	 &lunapi_t::version ,
	 "Version of Luna" );
  
  //
  // lunapi_t engine class
  //
  
  py::class_<lunapi_t>(m, "luna")
        
    .def( "read_sample_list" ,
	  &lunapi_t::read_sample_list,
	  "Load a sample list from a file" )
    .def( "build_sample_list" ,
	  &lunapi_t::build_sample_list,
	  "Load a sample list from a file" )
    .def( "get_sample_list" ,
          &lunapi_t::sample_list,
          "Return the loaded sample list" )

    .def( "insert_inst" , &lunapi_t::insert_inst )
    .def( "nobs" , &lunapi_t::nobs )
    .def( "clear" , &lunapi_t::clear )

    .def( "silence", &lunapi_t::silence )
    .def( "is_silenced" , &lunapi_t::is_silenced )

    .def( "flush" , &lunapi_t::flush )

    .def( "reset" , &lunapi_t::reset )
    
    .def("opt",py::overload_cast<const std::string &,const std::string &>(&lunapi_t::var),
		"Set an option value" )

    .def("get_opt",py::overload_cast<const std::string &>(&lunapi_t::var,py::const_ ),
	 "Show an option value" )
    .def("get_opts",py::overload_cast<const std::vector<std::string> &>(&lunapi_t::vars,py::const_),
	 "Show multiple option values" )
    .def("get_all_opts",py::overload_cast<>(&lunapi_t::vars,py::const_),
	 "Show all option values" )
    
    .def("clear_opt",&lunapi_t::dropvar,
	 "Clear an option" )
    .def("clear_opts",&lunapi_t::dropvars,
	 "Clear options" )
    .def("clear_all_opts",&lunapi_t::dropallvars,
	 "Clear all options" )

    .def("clear_ivars",&lunapi_t::clear_ivars,
	 "Clear all individual-variables")

    .def( "inst" ,
	  py::overload_cast<int>
	  (&lunapi_t::inst,py::const_),
	  "Return a lunapi-instance object from a sample list" )

    .def( "inst" ,
	  py::overload_cast<const std::string&>
	  (&lunapi_t::inst,py::const_),
	  "Generate an empty lunapi-instance" )

    .def( "inst" ,
	  py::overload_cast<const std::string&,const std::string &>
	  (&lunapi_t::inst,py::const_),
	  "Generate an lunapi-instance with attached EDF" )

    .def( "inst" ,
	  py::overload_cast<const std::string&,const std::string &,const std::string&>
	  (&lunapi_t::inst,py::const_),
	  "Generate an lunapi-instance with attached EDF & annotation" )

    .def( "inst" ,
	  py::overload_cast<const std::string&,const std::string &,const std::set<std::string>&>
	  (&lunapi_t::inst,py::const_),
	  "Generate an lunapi-instance with attached EDF & annotations" )

    .def( "get_n" , &lunapi_t::get_n)
    .def( "get_id" , &lunapi_t::get_id)
    .def( "get_edf" , &lunapi_t::get_edf)
    .def( "get_annot" , &lunapi_t::get_annot)

    .def( "import_db" ,
	  py::overload_cast<const std::string &>(&lunapi_t::import_db) )
    .def( "import_db_subset" ,
	  py::overload_cast<const std::string &,const std::set<std::string> &>(&lunapi_t::import_db) )

    .def("eval",&lunapi_t::eval,
	 "Evaluate a Luna command sequence given an attached EDF" ) 
  
    .def("commands",&lunapi_t::commands,
       "List commands resulting from a prior eval()" )

    .def("strata",&lunapi_t::strata,
	 "List command/strata tuples resulting from a prior eval()" )

    .def("vars",&lunapi_t::variables,
	 "List variables (columns) from a table (defined by a command/strat pair) from a prior eval()")

    .def("table",py::overload_cast<const std::string &,const std::string &>(&lunapi_t::results,py::const_) ,
	 "Return a result table (defined by a command/strata pair) from a prior eval()" )

    .def("tables",py::overload_cast<>(&lunapi_t::results,py::const_) ,
	 "Return a result table (defined by a command/strata pair) from a prior eval()" );

  //
  // lunapi_inst_t : individual instance (EDF/annotation pair)
  //

  py::class_<lunapi_inst_t, std::shared_ptr<lunapi_inst_t> >(m, "inst")

    // .def(py::init<const std::string &>(),
    // 	 py::arg( "id" ) = "id1" )

    .def( "attach_edf", &lunapi_inst_t::attach_edf,
	  "Attach an EDF" ,
	  "edffile"_a )
    .def( "attach_annot",&lunapi_inst_t::attach_annot,
	  "Attach an annotation file to the current EDF" ,
	  "annotfile"_a )

    
    .def( "refresh", &lunapi_inst_t::refresh,
	  "Reattach the current EDF")
    .def( "drop", &lunapi_inst_t::drop,
	  "Drop the current EDF" )
    
    .def( "channels", &lunapi_inst_t::channels,
	  "Return a list of channel labels" )
    .def( "chs", &lunapi_inst_t::channels,
	  "Return a list of channel labels" )
    .def( "has_channels", &lunapi_inst_t::has_channels,
	  "Return boolean for whether channels exist (with aliasing)" )
    .def( "has", &lunapi_inst_t::has_channels,
	  "Return boolean for whether channels exist (with aliasing)" )


    
    .def( "annots", &lunapi_inst_t::annots,
	  "Return a list of all annotations class labels" )
    .def( "fetch_annots", &lunapi_inst_t::fetch_annots,
	  "Return a list of intervals for selected annotations" )
    .def( "fetch_full_annots", &lunapi_inst_t::fetch_full_annots,
	  "Return a list of intervals and meta-data for selected annotations" )

    .def( "has_annots" , &lunapi_inst_t::has_annots,
	  "Return boolean for whether annotations exist (with aliasing)" )

    .def( "has_staging" , &lunapi_inst_t::has_staging,
	  "Return boolean for whether valid staging annotations exist" )
    
    .def( "stat" , &lunapi_inst_t::status,
	  "Return a dict of key details on the current EDF" )

    .def( "e2i" , &lunapi_inst_t::epochs2intervals ,
	  "Convert epoch numbers to interval tuples" ,
	  "e"_a )
    .def( "s2i" , &lunapi_inst_t::seconds2intervals ,
	  "Convert second (start/stop tuples) to interval tuples" ,
	  "s"_a )
    
    .def( "data",&lunapi_inst_t::data,
	  "Return an array of one or more channels for all records" ,
	  "chs"_a , "annots"_a , "time"_a = false )
    .def( "slice",&lunapi_inst_t::slice,
	  "Return a data matrix/column header tuple" ,
	  "i"_a , "chs"_a , "annots"_a , "time"_a = false )
    .def( "slices",&lunapi_inst_t::slices,
	  "Return a list of data matrices (one per epoch/interval)" ,
	  "i"_a , "chs"_a , "annots"_a , "time"_a = false )
    
    .def( "insert_signal" , &lunapi_inst_t::insert_signal,
	  "Insert a signal" ,
	  "label"_a , "data"_a , "sr"_a )
    .def( "update_signal" , &lunapi_inst_t::update_signal,
	  "Update a signal" , "label"_a , "data"_a )
    .def( "insert_annot" , &lunapi_inst_t::insert_annotation,
	  "Insert an annotation" ,
	  "label"_a , "intervals"_a , "durcol2"_a = false ) 

    .def("ivar",py::overload_cast<const std::string &,const std::string &>(&lunapi_inst_t::ivar),
	 "Set an individual-variable")
    .def("get_ivar",py::overload_cast<const std::string &>(&lunapi_inst_t::ivar,py::const_),
	 "Return an individual-variable")
    .def("ivars", &lunapi_inst_t::ivars,
	 "Return all individual-variables")
    .def("clear_ivar",&lunapi_inst_t::clear_ivar,
	 "Clear individual-variables")

    .def("eval",&lunapi_inst_t::eval,
	 "Evaluate Luna commands" )

    .def("proc",&lunapi_inst_t::eval_return_data,
	 "Similar to eval(), but returns all data tables" )

    .def("commands",&lunapi_inst_t::commands,
	 "List commands resulting from a prior eval()" )
    .def("strata",&lunapi_inst_t::strata,
	 "List command/strata tuples resulting from a prior eval()" )
    .def("vars",&lunapi_inst_t::variables,
	 "List variables (columns) from a table (defined by a command/strat pair) from a prior eval()")
    .def("table",py::overload_cast<const std::string &,const std::string &>(&lunapi_inst_t::results,py::const_) ,
	 "Return a result table (defined by a command/strata pair) from a prior eval()" )
    .def("tables",py::overload_cast<>(&lunapi_inst_t::results,py::const_) ,
	 "Return a result table (defined by a command/strata pair) from a prior eval()" )
        
    .def("__repr__",
	 [](const lunapi_inst_t & a)
	 {
	   std::string s = "<lunapi-instance id:" + a.get_id();
	   const std::string f1 = a.get_edf_file();
	   const std::string f2 = a.get_annot_files();
	   if ( f1 != "" ) s += " edf:" + f1;
	   if ( f2 != "" ) s += " annot:" + f2;
	   s += ">";
	   return s;
	 }
	 );
  


  
  
}

