ods path sashelp.tmplmst(read) sasuser.templat(update);

data policyDataset;                                                                                                                              
	length state $ 10;
	/*length policyID $ 20;*/
	/*input policyID	$	vioNumber	state	$;*/
	input policyID	vioNumber	state	$;

   datalines;                                                                                                                           
3	74.00	Experiment
2	13.40	Experiment
1	40.00	Experiment
6	75.10	Experiment
5	50.20	Experiment
4	17.50	Experiment
;

run;

proc format;                                                                                                                            
   value policy 1='Seq / Strict QoS'
   				2='Seq / QoS First'
				3='Seq / Eff First'
				4='RW / Eff First'
				5='RW / QoS First'
				6='RW / Strict QoS'
;
run;

/*options pageno=1 nodate;
goptions colors=(none);*/
/*goptions colors=;

ods html style=statistical;

option gstyle;

goptions reset=all device=jpeg hsize=13cm vsize=15cm;

ODS GRAPHICS / IMAGEFMT =JPEG;

ods jpeg 
     gpath="\\Client\D$\\Dropbox\\research\\MLScheduler\\tempPictures\\" (url="images/")
     image_dpi=300
     style=statistical;*/

/*  Statdoc	Seaside Seasideprinter	Journal*/
ods html style=Printer;
goptions reset=all device=png xpixels=600 ypixels=310;
title1 ;

/*goptions reset=all*/

axis1 label=none value=none ;                                                                                                            
axis2 ORDER =(0 TO 100 BY 15) label=(angle=90 "J48 Rejection Rate (Percent)") ;
axis3 label=none;

legend1 label=('Phase') frame;

proc gchart data=policyDataset;                                                                                                                  
   	vbar policyID / discrete sumvar=vioNumber mean 
                /*maxis=axis1*/ raxis=axis2 gaxis=axis3 
                 legend=legend1
				/*midpoints=.5 to 6 by .5, 30*/
;

	format policyID policy.;

	label 	
			policyID	= 'Workload Type / Policy';
run;   

/*ods _all_ close; 
ods listing;
*/
