
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


  // creates a new instance with ID 'id1'
  
  lunapi_t luna( "id1" );

  
  // attach an EDF (parses header, does not pull records until neeeded)
  
  luna.attach_edf( "learn-nsrr01.edf" ) ;

  
  // attach some annotations from a file
  
  luna.attach_annot( "learn-nsrr01-profusion.xml" );

  
  // evaluate a Luna command:
  //  luna learn-nsrr01.edf -s HEADERS
    
  bool okay = luna.eval( "HEADERS" ) ;


  // problem?

  if ( okay )
    {
      std::cerr << "problem, bailing...\n";
      std::exit(1);
    }
  
  
  // otherwise, pull the results from the previous eval() run:
  //  destrat out.db +HEADERS -r CH 
  
  rtable_t table = luna.table( "HEADERS" , "CH" );
  

  // dump outputs to stdout

  std::cout << table.dump() ; 

    // obtain list of all commands/strata from the prior run:
  
  std::vector<std::pair<std::string,std::string> > strata = luna.strata();

  
  // note: "baseline" strata use code 'BL', i.e. these are equivalent:
  //  destrat out.db +HEADERS
  //  rtable_t table = luna.table( "HEADERS" , "BL" );
  // note: if multiple strata X and Y, use X_Y
  

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
  
  std::tuple<Eigen::MatrixXd,std::vector<std::string> > R = luna.slice( lint , "EEG,EEG_sec" , "Arousal,W,NX" );

  // signals
  const Eigen::MatrixXd & X = std::get<0>(R);

  // labels
  const std::vector<std::string> & labels = std::get<1>(R);

  // outputs: first column is time (seconds from EDF start)
  std::cout << " pulled matrix " << X.rows() << " rows x " << X.cols() << " cols\n";

  std::cout << X << "\n";

  std::cout << " column labels\n" << Helper::stringize( labels ) << "\n";

  
 
}


