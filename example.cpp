
// An example C/C++ program that uses the LunaAPI library

#include "luna.h"

#include <iostream>
#include <string>
#include <cstdlib>

// required:
extern globals global;
extern writer_t writer;
extern logger_t logger;
extern freezer_t freezer;


int main()
{


  // always call init() before using the library
  
  lunapi_t::init();


  // file to attach

  const std::string edffile = "learn-nsrr01.edf";

  const std::string annotfile = "learn-nsrr01-profusion.xml";

  
  // creates a new instance with ID 'id1'
  
  lunapi_t luna( "id1" );

  
  // attach an EDF (parses header, does not pull records until neeeded)
  
  bool okay = luna.attach_edf( edffile );

  if ( okay ) 
    std::cout << "attached EDF\n";
  else    
    {
      std::cout << "** could not attached " << edffile << "\n";
      std::exit(1);
    }
  
  // attach some annotations from a file
  
  okay = luna.attach_annot( annotfile );

  if ( okay )
    std::cout << "attached annotations\n";
  else	
    {
      std::cout << "** could not attached " << annotfile << "\n";
      std::exit(1);
    }

  // evaluate a Luna command:
  //  luna learn-nsrr01.edf -s HEADERS
    
  std::string console = luna.eval( "HEADERS" ) ;

  std::cout << "---------------------------------------------------------------\n"
	    << console
	    << "---------------------------------------------------------------\n";

  // problem?
  
  if ( globals::problem )
    {
      std::cerr << "problem, bailing...\n";
      std::exit(1);
    }
  
  
  // otherwise, pull the results from the previous eval() run:
  //  destrat out.db +HEADERS -r CH 
  
  rtable_t table = luna.table( "HEADERS" , "CH" );
  

  // dump outputs to stdout

  std::cout << table.dump() ; 
 
  //
  // --- second command
  //
  //  luna learn-nsrr01.edf -s ' MASK ifnot=N2 & RE & PSD sig=EEG dB spectrum '
  
  console = luna.eval( "MASK ifnot=N2 & RE & PSD sig=EEG dB spectrum" );
  
  std::cout << "---------------------------------------------------------------\n"
	    << console
	    << "---------------------------------------------------------------\n";

  // obtain list of all commands/strata from the prior run:
  
  std::vector<std::pair<std::string,std::string> > strata = luna.strata();
 
  // note: "baseline" strata use code 'BL', i.e. these are equivalent:
  //  destrat out.db +HEADERS
  //  rtable_t table = luna.table( "HEADERS" , "BL" );
  // note: if multiple strata X and Y, use X_Y

  for (int t=0; t<strata.size(); t++)
    std::cout << "cmd = " << strata[t].first << "\t"
	      << "strata = " << strata[t].second << "\n";

  
  std::cout << "band power stats\n\n"
	    << luna.table( "PSD" , "B_CH" ).dump()
	    << "\n";
    
  std::cout << "spectral power stats\n\n"
	    << luna.table( "PSD" , "CH_F" ).dump()
	    << "\n";

  std::cout << "\n-------------------------------------------------------\n\n";

  
  //
  // ---- pulling signal/annotation data -----
  //

  // get information on channels and annotations on the attached EDF
  std::cout << " channels\n" << Helper::stringize( luna.channels() ) << "\n";

  std::cout << " annots\n" << Helper::stringize( luna.annots() ) << "\n";


  // specify one or more epochs (1-based)
  
  std::vector<int> e = { 1 , 2 , 3 } ; 

  // convert to time-point intervals 

  lint_t lint = luna.epochs2intervals( e );

  // use slice() to return a Eigen matrix and column label tuple:
  //  2nd and 3rd params are comma-delimited lists of channel/annotations

  // similar to luna MATRIX command; e.g. assumes signals have similar SRs

  
  std::vector<std::string> chs = { "EEG" , "EEG_sec" };
  std::vector<std::string> annots = { "Arousal" , "W", "NX" };
  // nb. as a test, NX does not exist - should be returned as all 'nan'
  
  std::tuple<std::vector<std::string>,Eigen::MatrixXd> R = luna.slice( lint , chs , annots , true );

  // signals
  const Eigen::MatrixXd & X = std::get<1>(R);

  // labels
  const std::vector<std::string> & labels = std::get<0>(R);

  // outputs: first column is time (seconds from EDF start)
  std::cout << " pulled matrix " << X.rows() << " rows x " << X.cols() << " cols\n";

  std::cout << X << "\n";

  std::cout << " column labels\n" << Helper::stringize( labels ) << "\n";

  
 
}


