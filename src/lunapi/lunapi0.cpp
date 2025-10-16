
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

  m.def( "fetch_doms" ,
	 &lunapi_t::fetch_doms ,
	 "Fetch all command domains" );
  m.def( "fetch_cmds" ,
	 &lunapi_t::fetch_cmds ,
	 "Fetch all commands" );
  m.def( "fetch_params" ,
	 &lunapi_t::fetch_params ,
	 "Fetch all parameters for a command" );
  m.def( "fetch_tbls" ,
	 &lunapi_t::fetch_tbls ,
	 "Fetch all tables for a command" );
  m.def( "fetch_vars" ,
	 &lunapi_t::fetch_vars ,
	 "Fetch all variables for a command/table" );

  m.def( "fetch_desc_dom" ,
         &lunapi_t::fetch_desc_dom ,
         "Description for a domain" );
  m.def( "fetch_desc_cmd" ,
         &lunapi_t::fetch_desc_cmd ,
         "Description for a command" );
  m.def( "fetch_desc_param" ,
         &lunapi_t::fetch_desc_param ,
         "Description for a command/parameter" );
  m.def( "fetch_desc_tbl" ,
         &lunapi_t::fetch_desc_tbl ,
         "Description for a command/table" );  
  m.def( "fetch_desc_var" ,
         &lunapi_t::fetch_desc_var ,
         "Description for a command/table/variable" );

  
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
    .def( "set_sample_list",
	  &lunapi_t::set_sample_list,
	  "Set sample list directly" )
    .def( "get_sample_list" ,
          &lunapi_t::sample_list,
          "Return the loaded sample list" )
    .def( "validate_sample_list" , 
	  &lunapi_t::validate_sample_list ,
	  "Validate an attached sample list" )
    .def( "insert_inst" , &lunapi_t::insert_inst )
    .def( "nobs" , &lunapi_t::nobs )
    .def( "clear" , &lunapi_t::clear )
    
    .def( "silence", &lunapi_t::silence )
    .def( "is_silenced" , &lunapi_t::is_silenced )

    .def( "flush" , &lunapi_t::flush )
    .def( "reinit" , &lunapi_t::re_init )
    .def( "reset" , &lunapi_t::reset )
    
    .def( "include" ,
	  &lunapi_t::includefile ,
	  "Include a @parameter-file" )

    .def( "aliases" ,
	  &lunapi_t::aliases ,
	  "Return table of signal & annotation aliases/mappings" )
    
    .def("opt",py::overload_cast<const std::string &,const std::string &>(&lunapi_t::var),
	 "Set an option value" )
    
    .def("get_opt",py::overload_cast<const std::string &>(&lunapi_t::var,py::const_ ),
	 "Show an option value" )
    .def("get_opts",py::overload_cast<const std::vector<std::string> &>(&lunapi_t::vars,py::const_),
	 "Show multiple option values" )
    .def("get_all_opts",py::overload_cast<>(&lunapi_t::vars,py::const_),
	 "Show all option values" )
    
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
	  "Generate an lunapi-instance" )
    
    .def( "empty_inst" ,
	  py::overload_cast<const std::string&,const int, const int, const std::string&, const std::string&>
	  (&lunapi_t::inst,py::const_),
	  "Generate an empty lunapi-instance of fixed record size" )

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
    
    .def("desc",&lunapi_t::desc,
	 "Table of basic descripives for all individuals" )
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
	  "Attach an EDF" )	  
    .def( "attach_annot",&lunapi_inst_t::attach_annot,
	  "Attach an annotation file to the current EDF" ,
	  "annotfile"_a )
    .def( "refresh", &lunapi_inst_t::refresh,
	  "Reattach the current EDF")
    .def( "drop", &lunapi_inst_t::drop,
	  "Drop the current EDF" )
    
    .def( "desc" , &lunapi_inst_t::desc,
	  "Return basic descriptive information" )
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
    .def("clear_selected_ivar",&lunapi_inst_t::clear_selected_ivar,
	 "Clear selected individual-variables")

    .def("eval",&lunapi_inst_t::eval,
	 "Evaluate Luna commands" )

    .def("eval_lunascope",
	 [](lunapi_inst_t& self, const std::string& cmd){
	   py::gil_scoped_release r;
	   return self.eval(cmd); // long C++ work, no Python API
	 },
	 "Evaluate Luna commands without holding the GIL")

    .def("eval_dummy", // debug code only
	 [](lunapi_inst_t& self, const std::string& cmd){
	   py::gil_scoped_release r;   
	   return self.eval_dummy(cmd);       
	 },
	 "Evaluate Luna commands without holding the GIL")
    
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

    .def( "get_id", [](const lunapi_inst_t & a) { return a.get_id(); } )

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



  //
  // segsrv_t : segment-server instance (linked to a single lunapi_inst_t)
  //
  
  py::class_<segsrv_t>(m, "segsrv")
    .def(py::init<lunapi_inst_ptr>())
    .def( "populate", &segsrv_t::populate,
	  "Initiate segment-server channels, annots" ,
	  "chs"_a , "anns"_a )
    
    .def( "populate_lunascope",
	  []( segsrv_t & self ,
	      const std::vector<std::string>& chs,
	      const std::vector<std::string>& anns ) -> int {
	    py::gil_scoped_release r;
	    return self.populate( chs , anns );
	  },	  
	  "Initiate segment-server channels, annots" ,
	  "chs"_a , "anns"_a )
    
    .def( "set_window", &segsrv_t::set_window,	  
	  "Define current window" ,
	  "start"_a , "stop"_a )
    .def( "get_signal", &segsrv_t::get_signal )
    .def( "get_timetrack", &segsrv_t::get_timetrack )
    .def( "get_time_scale", &segsrv_t::get_time_scale )
    .def( "set_scaling", &segsrv_t::set_scaling )
    .def( "fix_physical_scale", &segsrv_t::fix_physical_scale )
    .def( "empirical_physical_scale", &segsrv_t::empirical_physical_scale )
    .def( "free_physical_scale", &segsrv_t::free_physical_scale )
    .def( "get_scaled_signal", &segsrv_t::get_scaled_signal )
    .def( "get_gaps" , &segsrv_t::get_gaps )

    .def( "set_epoch_size", &segsrv_t::set_epoch_size )
    .def( "calc_bands", &segsrv_t::calc_bands ) // say which channels to do this for
    .def( "calc_hjorths" , &segsrv_t::calc_hjorths )
    .def( "nepochs" , &segsrv_t::nepochs )

    .def( "get_epoch_size" , &segsrv_t::get_epoch_size )
    //    .def( "get_epoch_timetrack" , &segsrv_t::get_epoch_timetrack )
    .def( "get_bands", &segsrv_t::get_bands ) // actually return the final epoch x band matrix for channel ch
    .def( "get_hjorths" , &segsrv_t::get_hjorths )

    //    .def( "get_ungapped_total_sec" , &segsrv_t::get_ungapped_total_sec )
    .def( "get_total_sec" , &segsrv_t::get_total_sec )
    .def( "get_total_sec_original" , &segsrv_t::get_total_sec_original )
    .def( "is_window_valid" , &segsrv_t::is_window_valid )
    .def( "get_window_left"  , &segsrv_t::get_window_left )
    .def( "get_window_right" , &segsrv_t::get_window_right )
    .def( "get_window_left_hms" , &segsrv_t::get_window_left_hms )
    .def( "get_window_right_hms" , &segsrv_t::get_window_right_hms )
    .def( "get_clock_ticks" , &segsrv_t::get_clock_ticks )
    .def( "get_hour_ticks" , &segsrv_t::get_hour_ticks )
    .def( "get_window_phys_range" , &segsrv_t::get_window_phys_range )
    .def( "get_ylabel" , &segsrv_t::get_ylabel )
    .def( "throttle" , &segsrv_t::throttle )
    .def( "input_throttle" , &segsrv_t::input_throttle )
    .def( "summary_threshold_mins" , &segsrv_t::summary_threshold_mins )
    .def( "serve_raw_signals", &segsrv_t::serve_raw_signals )
    .def( "get_summary_stats", &segsrv_t::get_summary_stats )
    .def( "get_summary_timetrack", &segsrv_t::get_summary_timetrack )

    .def( "compile_evts" , &segsrv_t::compile_evts )
    .def( "get_evnts_xaxes" , &segsrv_t::get_evnts_xaxes )
    .def( "get_evnts_yaxes" , &segsrv_t::get_evnts_yaxes )
    .def( "set_evnt_format6" , &segsrv_t::set_annot_format6 )
    .def( "get_evnts_xaxes_ends" , &segsrv_t::get_evnts_xaxes_ends )
    .def( "get_evnts_yaxes_ends" , &segsrv_t::get_evnts_yaxes_ends )
    .def( "fetch_all_annots", &segsrv_t::fetch_all_evts )
    .def( "fetch_annots" , &segsrv_t::fetch_evts ); 

}

