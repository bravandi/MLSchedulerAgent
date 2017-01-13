/* Set the graphics environment */                                                                                                      
goptions reset=all border cback=white htitle=12pt htext=12pt;

data dataset;                                                                                                                              
	/*length policy $ 20;*/
	input policy	SequentialRead	SequentialWrite	RWRead	RWWrite;

   datalines;                                                                                                                           
1	1	4	14	17.0

2	20	21.0	43.0	47.0

3	29.0	35.0	31.0	37.0

4	54	54	54	54
;                               
/* 4	58.85	60.63	58.85	60.63*/ 
run;
/*
1	0.028759	0.003363	0.045528	0.038491

2	0.089027	0.052663	0.057826	0.063158

3	0.104845	0.114378	0.082947	0.068663

4	0.588524	0.606282	0.588524	0.606282
*/
/*proc sort data=dataset out=new;
   by descending	policy;
run;*/

proc format;
   value po 1='StrictQoS' 2='QoSFirst' 3='EfficiencyFirst' 4='Default Scheduler';
run;

ods html style=Printer;
/*goptions reset=all device=png xpixels=400 ypixels=400;*/
title1 ;
                                                                                                                                        
axis3 label=none;

/* Define legend characteristics */                                                                                                     
legend1 label=('Algorithm') frame;  
                                                                                                                                        
/* Define the title */                                                                                                      
title1;

/* Define symbol characteristics */                                                                                                     
symbol1 interpol=join value=trianglefilled color=cxBA6C60 height=2 line=1;	/*SequentialRead*//*color=vibg			cx5674AF*/
symbol2 interpol=join value=trianglefilled color=cxBA6C60 height=2 line=2;	/*SequentialWrite*/ /*color=depk			cxBA6C60*/
symbol3 interpol=join value=squarefilled color=cx5674AF height=2 line=1;	/*RWRead*/
symbol4 interpol=join value=squarefilled color=cx5674AF height=2 line=2;	/*RWWrite	diamondfilled*/
symbol5 interpol=join value=dot color=cx000000 height=2 line=1;	/*RWWrite	diamondfilled*/
symbol6 interpol=join value=dot color=cx000000 height=2 line=2;	/*RWWrite	diamondfilled*/
                                                                                                                                        
/* Define legend characteristics */                                                                                                     
legend1 label=none frame;                                                                                                               
/* Define axis characteristics */                                                                                                       
axis1 label=("Policy") minor=none offset=(1,1);
axis2 label=(angle=90 "BN IOPS SLO Violation Percentage")
      order=(0 to 66 by 5) minor=(n=1);

proc gplot data=dataset;
   	plot (SequentialRead SequentialWrite RWRead RWWrite)*policy / overlay legend=legend1                                                                               
                                   haxis=axis1 vaxis=axis2;

	format policy po.;

	label 	SequentialRead		= 'Sequential IO Read'
			SequentialWrite		= 'Sequential IO Write'
			RWRead				= 'RandRW IO Read'
			RWWrite				= 'RandRW IO Write';
run;                                                                                                                                    
quit;  
