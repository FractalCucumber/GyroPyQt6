/////////////////////////////////////////////////////////////////////////////////////////
//PURPOSE:  Base application for ADSP-21489 KR3 usage for ARM
//
// Project   begin:  14.12.2011
// Last correction:  21.09.2015 
// Autor: O.I.Rakituanskiy 04.12.2014   Termo & RuchServoMotor control        
//       
//    Only for Device ¹ 03   vibro protocol       
////////////////////////////////////////////////////////////////////////////////////////
#include <Cdef21489.h>
#include <def21489.h>
//#include <21489.h>
#include <signal.h>
#include <sysreg.h>
#include <stdlib.h>
#include <string.h>
#include <SRU.h>
#include "Spi.h"
#include <math.h>
#include "crc8.h"
//
#define SRUDEBUG  // Check SRU Routings for errors.
//
// Procedures and Functions prototypes
float FLowPass(float invar);
void init_Timers(void);
void init_Timers_IRQ(void);
void tim0_ISR(int sign);
void tim1_ISR(int sign);
void init_DPI(void);	    	//makes UART0 signal connections to DPI pins
void init_UART(void);   	    //initializing UART
void write_UART(char *xmit, int len); // UART transfer message procedure
void wait(int cou);
void initPWM(void);
void initPCGA(int PCG_W);
void GetAsicData(void);
void GetTempData(void);
void motorCTL(int motPwr,float motAngl);
void findZeroPos(float angle);
void findRightPos(float angle);
//
void initUARTDMA_TX(int len);
void initUARTDMA_RX(void);
//
void UART_ISR(int sign);		//UART interrupt service routine
//	
void Sport1_ISR(int sign);		//SPORT1 interrupt service routine
//
void Sport3_ISR(int sign);		//SPORT2 interrupt service routine ***disable now!!!
void PWM_ISR(int sign);         //PWM interrupt service routine
//
void initPLL(void); //Configure the PLL for a core-clock of 320MHz and SDCLK of 160MHz
//
extern void init_SPORT0(void);
extern void init_SPORT1(void);
extern void init_SPORT2(void);
extern void init_SPORT3(void);
extern void init_SPORT4(void);
//
bool flag  = true;			// indicate flag
bool flag_T  = true;
bool flag_vel = false;
bool flag_IRQ1 = true;
bool flag_buf  = true;
bool flag_CONV = true;
bool flag_STOP = false;
bool flag_find_Zero = false;
bool flag_find_Right = false;
bool flag_vibration = false;
bool Flag_Vibro = false;
//
int len = 14;     //10 - to vibro.  34 - length of out pack = 34 bytes
int bufout[48];
char packout[48];
char packin[48];  // input chars buffer
int Cmd = 0;
int FrqVibr = 10;
int FrqNmb  = 100;
int Peltier = 10;
int SetVel = 0;

//
int PwMotor = 0;  // Zero Motor disabled
int index_V = 0;
//
int counter = 0;
int cou_Temp = 0;
int pwm_AL = 0;
int pwm_AL0 = 0;
int pwm_AL1 = 0;
int pwm_AL2 = 0;
int pwm_AL3 = 0;
int pwm_BL = 0;
int buftmp = 0;
unsigned int ubufmov = 0;
//
extern int usb_buf[]; 
extern int spi_bufB[]; 
extern int spi_buf[];  
extern int rx_buf0[];
extern int rx_buf1[];
extern int rx_buf2[];
extern int rx_temp[];
extern int temp_ADT[];
extern int Temp;
extern int tmp;
extern int Freq_Table[];
extern int Amp_Table[];
//
int AA = 0;
int BB = 0;
int CC = 0;
short T0 = 0;
short T1 = 0;
short T2 = 0;
short T3 = 0;
float Af = 0.0;
float Bf = 0.0;
float Cf = 0.0;
float enc_sin;
float enc_cos;
float enc_andl_2pi = 0.0;
float enc_angl = 0.0;
float enc_angl_dif = 0.0;
float enc_angl_old = 0;
float enc_angl_gr = 0;
const double pi = 3.14159265368979;
//
float angle = 0.0;
float angle_old = 0.0;
float angle_sm = 0.0;
float vel_angle = 0.0;
//
float vel_angl = 0.0;
float vel_angl_dps = 0.0;
float vel_angl_dif =0.0;
float err_vel = 0.0;
float integ_angl = 0.0;
float vibro = 0.0;
int   iVibro = 0;
float Vel_Target = 0.0;
//
int len_dif  = 128; //

float shift_anglMot = 0.0; // shift Agle of Motor from current Zero point
float motor_angl = 0.0;    // Agle of Motor position in radians

float GyroFilt = 0.0;
int buffer = 0;

int cou_init = 0; // counter initialisation time for shift Agle of Motor stand

int cou_temp = 0; // Temperature counter
int cou_pwm  = 0; // PWM period counter
int cou_div = 0;
int sct_angl = 0; // Angle counter
int sct_nmb  = 0; // Sector number
int cou_dif  = 0; // dif. counter 
int NAngle   = 0;  // amount of encoder half-cycles 
int sign_old = 0;  // enc_cos sign (old value)
int sign_new = 0;  // enc_cos sign (new value)
//
//unsigned char strLoad[30] = "ADSP-21489 user program\n";

int PCG_W = 30030;   // 1.5 ms                
int count,test;
int ks = 0; 
int cou_channel = 0;
int N_DUperiod =0;
//
//
unsigned int imask = 0;
unsigned int lirptl = 0;
//
// Coeff. for FLowPass  // F= 2kHz  PB= 100Hz
    static float delayA[5] = {0.0,0.0,0.0,0.0,0.0};
    static float znumA[4] = {
        2.0083366e-02,
        4.0166731e-02,
        2.0083366e-02
    };
    static float zdenA[3] = {
        .64135154,
        -1.5610181
    }; 
//    
float   max_vel = 0.0;
float   err_amp = 0.0;
float   integral_amp = 0.0;
float   K_amp_vel = 1;
/******************************************************************************/
/* Filter Solutions Version 9.0                  Nuhertz Technologies, L.L.C. */
/*                                                            www.nuhertz.com */
/*                                                            +1 602-206-7781 */
/* 2nd Order Low Pass Butterworth                                             */
/* Bilinear Transformation with Prewarping                                    */
/* Sample Frequency = 80 KHz                                               */
/* Standard Form                                                              */
/* Arithmetic Precision = 8 Digits                                            */
/*                                                                            */
/* Pass Band Frequency = 100 Hz                                             */
/*                                                                            */
/******************************************************************************/
/*                                                                            */
/* Input Variable Definitions:                                                */
/* Inputs:                                                                    */
/*   invar    double      The input to the filter                             */
/*   initvar  double      The initial value of the filter                     */
/*   setic    int         1 to initialize the filter to the value of initvar  */
/*                                                                            */
/* There is no requirement to ever initialize the filter.                     */
/* The default initialization is zero when the filter is first called         */
/*                                                                            */
/******************************************************************************/
/*                                                                            */
/* This software is automatically generated by Filter Solutions.  There are   */
/* no restrictions from Nuhertz Technologies, L.L.C. regarding the use and    */
/* distributions of this software.                                            */
/*                                                                            */
/******************************************************************************/
float FLowPass(float invar) 
{
  float sumnum, sumden;  int i;

        sumden=0.0;
        sumnum=0.0;
        for (i=0;i<=1;i++)
          {
            delayA[i] = delayA[i+1];
            sumden += delayA[i]*zdenA[i];
            sumnum += delayA[i]*znumA[i];
          }
        delayA[2] = invar - sumden;
        sumnum += delayA[2]*znumA[2];
        return sumnum;
}
//--------------------------------------------------------------------
void initUARTDMA_TX(int len)     // len is length of pack in bytes
{
   *pUART0TXCTL = 0;                // STOP UART Tx 
   *pIIUART0TX = (char)packout;     // pointer to output buffer
   *pIMUART0TX = 1;
   *pCUART0TX  = len;                // packet length = 34 byte now!!!
   *pUART0TXCTL = UARTEN | UARTDEN;	// Start Transmit
}
//
void initUARTDMA_RX(void)     // Get Control Command
{
   *pUART0RXCTL = 0;                // STOP UART Tx 
   *pIIUART0RX = (char)packin;      // pointer to output buffer (length = 48 chars)
   *pIMUART0RX = 1;
   *pCUART0RX  = 8;                 // packet length = 2+2 byte now!!!
   *pUART0RXCTL = UARTEN | UARTDEN;	// Start Receive	
}                         
//---------------------------------------------------------------------
void initPLL(void)
{
int i, pmctlsetting;

// CLKIN= 20 MHz, Multiplier= 16, Divisor= 2, 
// CCLK_SDCLK_RATIO 2.5 - for DDR2.
// Fcclk = (CLKIN * 2 * M) / (N * D)  =  20MHz*2*16/(2*1) = 320 MHz Fcore
// VCO frequency = 2*Finput*PLLM = 2*20*16 = 640 <= fVCOmax (800 MHz)
// M = 1 to 64, N = 2,4,8,16 and D = 1 if INDIV = 0, D = 2 if INDIV = 1   
    pmctlsetting=SDCKR2_5|PLLM16|DIVEN|PLLD2;
    *pPMCTL= pmctlsetting;
//
    pmctlsetting|= PLLBP;	//Setting the Bypass bit
    pmctlsetting^= DIVEN;	//Clearing the DIVEN bit
    *pPMCTL= pmctlsetting;	// Putting the PLL into bypass mode
//    
//Wait for around 4096 cycles for the pll to lock.
    for (i=0; i<5000; i++)    asm("nop;");
//      
    pmctlsetting = *pPMCTL;
	pmctlsetting ^= PLLBP;          //Clear Bypass Mode
	*pPMCTL = pmctlsetting;

//Wait for around 15 cycles for the output dividers to stabilize.
     for (i=0; i<16; i++) asm("nop;");             
}
//-----------------------------------------------------------------------
void initPCGA(int PCG_W)
{	
	*pPCG_CTLA0 = 0;						// halt PCGA    
	*pPCG_PW = PCG_W;                   	// PW_FSA
	*pPCG_CTLA1 = 3003; 					// CLKA_DIV
	*pPCG_CTLA0 = 60060 | ENCLKA | ENFSA; 	// FSA_DIV
	
}
//++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ 
void DAIPB10_ISR(int sign)
{
	int roc = *pDAI_IRPTL_H; // reset DAI Hi-pri. int.
	
//	 if (flag) SRU2(HIGH, DPI_PB13_I); 
//	   else SRU2(LOW, DPI_PB13_I);
//      flag = !flag; 		
		
}
//-------------------------------------------------------------------------
void GetAsicData(void)
{
        SRU(LOW, DAI_PB04_I);  // DAI_PB04_I make ~CS for ASIC	                                                          
//     
          init_SPORT1();    // generate extern Clk and FS for SPORT0  
          init_SPORT0();    // start Data request to SPORT0 	
}
//--------------------------------------------------------------------------
void GetTempData(void)
{
	SRU(LOW, DAI_PB04_I);   // DAI_PB04_I make ~CS for ASIC
// start Temperature Data reques
//     	init_SPORT3();      // generate extern Clk and FS for SPORT2     
//     	init_SPORT2();	  	// start Data request to SPORT3 
}
//--------------------------------------------------------------------------
void motorCTL(int motPwr,float motAngl)
{    // pole range = 360/13 = 27.6923 dgr
     // sector range 27.7/6 = 4.61538 dgr
     // sectors amount      = 78
  float angleA,angleC;
  int max_fase;
//     		
		BB = (int)((motPwr)*sinf(motAngl));
		
		angleA = motAngl + 2*pi/3;
//		if (angleA >= 2*pi) angleA -= 2*pi;	
			
		AA = (int)((motPwr)*sinf(angleA));
		
		angleC = motAngl - 2*pi/3;
//		if (angleC < 0) angleC += 2*pi;
		
    	CC = (int)((motPwr)*sinf(angleC));
    	
    	if (AA > BB) max_fase = AA;
		else max_fase = BB;
		if (CC > max_fase) max_fase = CC; // 
//		
		max_fase = 2000 - max_fase; //was 1000 max_fase=ostatok do maxPower(1000) 	
		AA += max_fase;
		BB += max_fase;	
		CC += max_fase;
			
}
//
void findZeroPos(float angle)
{
    if (angle > 40) {SetVel = -30;}
     else if (angle < -40) {SetVel = 30;}
      else {flag_find_Zero = false; SetVel = 0; flag_STOP = true;} 
}
//
void findRightPos(float angle)
{
   if (angle > -17000) {SetVel = -30;}	
    else {flag_find_Right = false; SetVel = 0; flag_STOP = true;} 
}
//++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
void TMZLI_ISR(int sign)  // (low prior.) Core timer ISR  400Hz 
{  
                    	  	 
}
//----------------------------------------------------------------------------
void IRQ1_ISR(int sign)
{	  

    wait(10); 	 	
      readADC_SPI();	 // Get Encoder Data      	 			
}
//----------------------------------------------------------------------------
void IRQ0_ISR(int sign)
{
     	 asm("nop;");    // Not use now, but reserved to Defence Input
}
//-----------------------------------------------------------------------------
void spi_ISR(int sign)   // Encoder Data received (2 words)
{						 // 80kHz
//
	*pSPIDMAC = 0;
 	*pSPICTL = 0x0;	// disable SPI 
	*pSPISTAT = 0xff;
//	 Get Encoder Data
	enc_sin = spi_buf[0];  
	enc_cos = spi_buf[1];
//			
	if (enc_sin >= 0)
	 {
	  if (enc_cos > enc_sin) enc_angl = (float)(atanf(enc_sin/enc_cos));	
	   else
	     {  
	      if (enc_sin > (-enc_cos)) enc_angl = pi/2 + (float)(atanf(-enc_cos/enc_sin));
	       else enc_angl = pi + (float)(atanf(enc_sin/enc_cos));
	      }
	 }
	else  
	 {
	  	 if (enc_sin > enc_cos) enc_angl = (float)(atanf(enc_sin/enc_cos)) - pi;  
	  	  else 
	  	    { 
	  	     if (enc_sin < (-enc_cos)) enc_angl = (float)(atanf(-enc_cos/enc_sin)) - pi/2;
	  	      else enc_angl = (float)(atanf(enc_sin/enc_cos));
	  	    }
	 }
	  enc_angl = enc_angl + pi; // shift range from (-pi -> +pi) to (0 -> 2pi)
	if ((enc_angl_old - enc_angl) > pi) N_DUperiod = N_DUperiod + 1; 
	if ((enc_angl - enc_angl_old) > pi) N_DUperiod = N_DUperiod - 1;
//	if (N_DUperiod < 1) N_DUperiod = N_DUperiod + 360;
//	if (N_DUperiod > 359) N_DUperiod = 0;
	enc_angl_old = enc_angl;
// Zero marker:  if(metka_0 = true) N_DUperiod = 0;
	enc_angl = (enc_angl + N_DUperiod*2*pi)/360;  
}
//
void spiB_ISR(int sign)   // USB Data transmit (8 bytes)
{
//	SRU2(LOW, DAI_PB03_I);
//	wait(0xff);
}
//------------------------------------------------------------------------------
void tim0_ISR(int sign)  // Interrupt service routine 
{ 	  int i,ks;	   
//		
		*pTM0STAT = TIM0IRQ | TIM0OVF; // reset Tim0 IRQ event (*pTMSTAT = 0x11;)	
//	      

		GetAsicData();  	   	    
}
//
void tim1_ISR(int sign)  // Interrupt service routine
{int i;
	
		*pTM1STAT = TIM1IRQ | TIM1OVF; // reset Tim1 IRQ event	(*pTMSTAT = 0x22;)
/*		
       cou_pwm++;       // 1000 Hz
        if (cou_pwm > 2999)         // 199 200Hz event frequrncy
         { 
         	if (index_V >= 47) 	
         	{
         		Flag_Vibro = false;
         		PwMotor = 0; 
         		flag_STOP = true; 
         		SRU(LOW, DAI_PB17_I); 
         		flag_vibration = false;
         		Flag_Vibro = true;
         		}
         	else if (Flag_Vibro)
         	{
         		SetVel = Amp_Table[index_V];
         		FrqVibr = Freq_Table[index_V];
         		flag_vibration = true; 
         		flag_STOP = false; 
         		SRU(HIGH, DAI_PB17_I);
         		index_V++;
         		Flag_Vibro = false;
         	}
         	else
         	{
         		PwMotor = 0; 
         		flag_STOP = true; 
         		SRU(LOW, DAI_PB17_I); 
         		flag_vibration = false;
         		Flag_Vibro = true;	
         	}
         	cou_pwm = 0;
         	}           // reset counter
*/		           
}
//-----------------------------------------------------------------------------------
void init_Timers(void)
{
	*pTM0CTL = IRQEN | PRDCNT | PULSE | TIMODEPWM ; //0x0d;
	*pTM1CTL = IRQEN | PRDCNT | PULSE | TIMODEPWM ; //0x0d;
//
	*pTM0PRD = 80000;    //200Hz  //27000	 29600  
	*pTM1PRD = 80000; //80Hz 400000; //200Hz    
//
	*pTM0W	= 2000;    // set pulse width timer0
	*pTM1W	= 2000;    // set pulse width timer1	
//
}
//------------------------------------------------------------------------------------
void init_Timers_IRQ(void)
{
	*pTM0CTL |= 0x10;  	// enable TIM0 interrupt
	*pTM1CTL |= 0x10;	// enable TIM1 interrupt	
}
//
void init_DPI()  // Route UART to DPI pinouts
{	
  SRU2(UART0_TX_O,DPI_PB09_I); // UART transmit signal is connected to DPI_PB9 pin 30
  SRU2(DPI_PB10_O,UART0_RX_I); // UART receive signal is connected to DPI_PB10 pin 31
//    
  SRU2(LOW,DPI_PB10_I);        // Set DPI_PB9 pinout to low-level  
  SRU2(HIGH,DPI_PBEN09_I);     // Enable DPI_PB9 as output      
  SRU2(LOW,DPI_PBEN10_I);      // Enable DPI DPI_PB10 as input  
}
//--------------------------------------------------------------------------------------
void init_UART(void)
{
// Sets the Baud rate for UART0	to 115200
	*pUART0LCR = UARTDLAB;  // enables access to Divisor register to set baud rate
	*pUART0DLL = 0x0b;      // 0x056 = 86.4 for divisor value  for peripheral clock of 160MHz
    *pUART0DLH = 0x00; 		// and gives a baud rate of 115200 bod  
// Configures UART0 LCR  
    *pUART0LCR = UARTWLS8;  				// word length 8 with no parity
                 // UARTPEN; 				// parity enable ODD parity
                 // UARTSTB ; 				// Two stop bits   
//                             
    *pUART0RXCTL = UARTEN;       //enables UART0 in receive mode
    *pUART0TXCTL = UARTEN;       //enables UART0 in transmit mode 
}
//--------------------------------------------------------------------------------
void UART_ISR(int sign)  // Receive control comand
{
//     (*pUART0RBR); // read byte from COM port;
//  if ((*pUART0LSR & UARTDR) == 1)
/*  
    if (flag) SRU2(LOW, DPI_PB13_I);
     else SRU2(HIGH, DPI_PB13_I);
      flag = !flag;
*/
 	 // ======= Cmd decoder ========
     Cmd =  ((packin[0] | (packin[1] << 8)) << 16) >> 16; // (16-bits word with sign) 
      if (Cmd == 11)                  // Temperature Chamber setting 
       {
         Peltier = ((packin[2] | (packin[3] << 8)) << 16) >> 16; // (16-bits word with sign) Peltier's parameter
         flag_STOP = true; 
       }
      if (Cmd == 33)                  // Start Rotation 
       {  SetVel = (packin[7] << 24) | (packin[6] << 16) | (packin[5] << 8) | packin[4]; // (integer format) 
         flag_STOP = false;
       }
      if (Cmd == 55)                  // Velocity setting
       {   SetVel = (packin[7] << 24) | (packin[6] << 16) | (packin[5] << 8) | packin[4]; // (integer format)
         flag_STOP = true;
       }
                                     // Stop rotation 
      if (Cmd == 0) {PwMotor = 0; flag_STOP = true; 
      	SRU(LOW, DAI_PB17_I); flag_vibration = false;
      	integral_amp = 0; K_amp_vel = 1; // !
      }
                                     // Find Zero position
      if (Cmd == 99) {flag_find_Zero = true; flag_STOP = false;}  
                                     // Find Right position
      if (Cmd == 100) {flag_find_Right = true; flag_STOP = false;} 
                                     // Start vibration
      if (Cmd == 77) 
       {
     	FrqVibr = ((packin[2] | (packin[3] << 8)) << 16) >> 16;  // Set vibration frequency
      	SetVel = (packin[7] << 24) | (packin[6] << 16) | (packin[5] << 8) | packin[4]; // (integer format)
     	flag_vibration = true; flag_STOP = false; SRU(HIGH, DAI_PB17_I);
     	//integral_amp = 0; K_amp_vel = 1; // 
		  K_amp_vel = 0.9 * (((-4.75368112e-09)*powf(FrqVibr, 4) +
                              (2.06569833e-06)*powf(FrqVibr, 3) +
                              (2.02236573e-04)*powf(FrqVibr, 2) +
                              1.60865286e-03*FrqVibr)) + 0.941254199; 
		if (K_amp_vel > 30) {K_amp_vel = 30;}
		if (K_amp_vel < 1) {K_amp_vel = 1;}
            integral_amp = 4 * K_amp_vel - 4; // / 0.25;                 
     /* */
     	}                 	                 
//
// Prepare to get control command	 							                    	                    	                  
          initUARTDMA_RX();         	  	
// echo ON
//  while ((*pUART0LSR & UARTTHRE) == 0) {;} // echoes back the value on to the hyperterminal screen   
//  		  *pUART0THR = value;            // write byte out   
//  while ((*pUART0LSR & UARTTEMT) == 0) {;} // poll to ensure UART has completed the transfer       
}
//**************************************************************************************
void Sport1_ISR(int sign)
{  int  a,ks,i,T;
//
	do {a = *pSPCTL1 & 0xc0000000;}
	 while(a != 0);	  			
	*pSPCTL1 = 0;
	*pSPCTL0 = 0; 
//	
    SRU(HIGH, DAI_PB04_I); // Clear ~CS   ~~|_|~~ 24us   				
//	++++++++++++++ MEMS-Gyro parameters ++++++++++++++++++++++++++++		
		
 		bufout[0] = 0x72;
   	    bufout[1] = (((int)(Vel_Target*1000) >>16) & 0xff); // 1
		bufout[2] = (((int)(Vel_Target*1000) >>8) & 0xff);      
		bufout[3] = (((int)(Vel_Target*1000)) & 0xff);            
		
	     bufout[4] = (((int)(vel_angle*200) >>16) & 0xff);     // 2
         bufout[5] = (((int)(vel_angle*200) >>8) & 0xff);  
	     bufout[6] = (((int)(vel_angle*200)) & 0xff);  
	     // åñëè ïðîðåæèâàíèå ïåðåìåííîå, òî íàäî äåëèòü íà íåãî è äîìíîæàòü íà 10000, ÷òîáû ÷èñëà íå ìåíÿëèñü,
	     // èíà÷å íà ñòåíä èäóò ìåíüøèå çíà÷åíèÿ
	// vibro
		bufout[7] = (0); // 1
		bufout[8] = (0);      
		bufout[9] = (((int)flag_STOP) & 0xff); 
	
		   bufout[10] = (((int)(K_amp_vel*100) >>16) & 0xff);     // 4	
           bufout[11] = (((int)(K_amp_vel*100) >>8) & 0xff);  
	       bufout[12] = (((int)(K_amp_vel*100)) & 0xff);
	       bufout[13] = 0x27;
	       
	  for (i=0;i<len;i++)  { packout[i] =  (char)(bufout[i]);}     
	       
	    initUARTDMA_TX(len);            // start output pack  100Hz
}
//---------------------------------------------------------------------
void Sport3_ISR(int sign)  // Get Temperature (Climat Chamber)
{ int  a;
	do {a = *pSPCTL3 & 0xc0000000;}
	 while(a != 0);	 
	*pSPCTL3 = 0; 
	*pSPCTL2 = 0; 
//	
	    SRU(HIGH, DAI_PB04_I); //  Clear ~CS   ~~|_|~~ 24us 
//-------------------------------------	
//	  if (flag) SRU(HIGH, DAI_PB03_I); 
//	   else SRU2(LOW, DAI_PB03_I);
//         flag = !flag;
//-------------------------------------
/*    cou_temp++;
    if (cou_temp < 17)
     { 
       temp_ADT[3] += ((temp_ADT[0]<<19)>>18);
     } 
     else {
     	   cou_temp = 0;
     	   Temp = temp_ADT[3] >> 4;
     	   temp_ADT[3] = 0; 
          }
*/            
}
//
void Sport4_ISR(int sign)  // data to USB
{
	int  a;
	do {a = *pSPCTL4 & 0xc0000000;}
	 while(a != 0);	

}
//
//=========================================================================================

void initPWM(void)
{    // setting PWM parameters ----------------------------------------
    *pPWMPERIOD1 = 4000; //  Freq = Fperif/N = 160000000/2000 = (40KHz)
	*pPWMAL1 = (unsigned int)(-1999);   // 
	*pPWMDT1 = 700;
//      
//===========================================================================
    *pPWMPERIOD2 = 4000; //(40kHz)  2000; //  Freq = 160000000/2000 = (80KHz)
    *pPWMPERIOD3 = 4000; //         2000;
//    
	*pPWMA2 = (unsigned int)(-1999); //(-999);    // *pPWMAL2
	*pPWMB2 = (unsigned int)(-1999); //(-999);    // *pPWMBL2	
	*pPWMA3 = (unsigned int)(-1999); //(-999);    // *pPWMAL3 
//     
    *pPWMCTL1 = PWM_IRQEN; // enabled PWM1 irq. Element Pelt'e contlol
//       
    *pPWMCTL2 = PWM_IRQEN | PWM_PAIR | PWM_ALIGN; // enabled PWM2 irq.  
    *pPWMCTL3 = PWM_IRQEN | PWM_PAIR | PWM_ALIGN; // enabled PWM3 irq.  
//       
    *pPWMGCTL =  PWM_EN1 | PWM_EN2 | PWM_EN3; //   	
}
//*************************  PWM - main synchronization  ******************************
void PWM_ISR(int sign) // PWM ISR frequency  =  40kHz realy! (37kHz...43kHz)
{	 	
	short PWM_stat = *pPWMGSTAT;
	int periods = 0;
//-------------------------------------------------------------
        cou_div++;
//         
         enc_angl_gr = 5729.578*enc_angl; //  enc_angl
//        enc_angl_gr òî÷íî íå 4 èëè 9 ðàç ñóììèðóåòñÿ?
		if (flag_vibration) ////////////////////////////////////////////////////////////////////
		{
		FrqNmb = 40000/FrqVibr; // âîò çäåñü îøèáêà
		iVibro++;
			if (iVibro > FrqNmb) // äîëæíî ïîìî÷ü
			{
				err_amp = (SetVel*5 - max_vel)/(SetVel*5);
				integral_amp += err_amp;

				K_amp_vel = (float)(err_amp*0.5 + integral_amp*0.25 + 1);
				iVibro = 0;
				max_vel = 0;
			} 
		}

         if (cou_div > 4) // || (iVibro > FrqNmb)) //event frequency 8000 Hz
          {  
      	  	 cou_div = 0;     
          	 motor_angl = 13*enc_angl; 
          	 periods = 0.5*motor_angl/pi;
          	 motor_angl = motor_angl - periods*2*pi;
// --  ----------------------------------------------------------------------------------------          	 
         	 if (cou_init < 6000) 	// +++++ start initialization
          	  {                     // One time !
          	 	cou_init++;
          	 	motorCTL(400, 0.0); //was 400 => 0.2*POWERmax (go to nearest pole zero position)
          	 	N_DUperiod = 0;
          	 	shift_anglMot = motor_angl + 0.5*pi;       // Phase shift to 90 electrical Degrees
//          	 	 if (shift_anglMot >= 2*pi) shift_anglMot = shift_anglMot - 2*pi;
          	 	 integ_angl = 0;
          	  }  	 // +++++ end of initialization +++++++++++++++++++++++++++++++++++++++++++++++
          	 else    //  work with freq. = 2 kHz     	  
          	    { 
          	  	    motor_angl = motor_angl + shift_anglMot;         	                                        
          	  		 if (motor_angl >= 2*pi) motor_angl = motor_angl - 2*pi; 
          	    // if it's need to find Zero position
          	       if (flag_find_Zero) { findZeroPos(enc_angl_gr);}   //Zero position Ang.vel = 30gdr/s
          	    //                                  	                           
          	       if (flag_find_Right) { findRightPos(enc_angl_gr);} //170dgr position Ang.vel=30gdr/s 
          	    // 
          	    
// -- PI  regulator    -----      Amplitude Stabilization  -------------------------------------
			 if (flag_vibration)  // Start vibration 
			  {                   
				//FrqNmb = 4000/FrqVibr; // âîò çäåñü îøèáêà
				//iVibro++; 
				/*if (iVibro > FrqNmb) // â îäíîì ïåðèîäå FrqNmb èíòåðàöèé
				{
					err_amp = (SetVel*5 - max_vel)/(SetVel*5);
					integral_amp += err_amp;

					K_amp_vel = (float)(err_amp*0.5 + integral_amp*0.25 + 1);
					iVibro = 0;
					max_vel = 0;
				} 
				else */
				if (vel_angle > max_vel) {max_vel = vel_angle;} // ìîæíî èñêàòü ñðåäíåå ìåæäó ìèíèìóìîì è ìàêñèìóìîì
		
				vibro = sinf(iVibro*2*pi/FrqNmb); 
				Vel_Target = SetVel*vibro; 
			  }
			  else Vel_Target = SetVel; 
	                	  
// -- PI  regulator    -----      Velocity Stabilization   ------------------------------------
          	  	    err_vel = (float)(Vel_Target*5*K_amp_vel - vel_angle); // resolution 0.1 degree
          	  	 if (flag_STOP) integ_angl = 0;
          	  	  else integ_angl += 0.009*err_vel;  // was 0.017
          	  	                             
          	  	     if (integ_angl > 1900) integ_angl = 1900;
          	  	     if (integ_angl < -1900) integ_angl = -1900;  
          	  	   if (SetVel == 0) integ_angl = 0;   
// --------------------------------------------------------------------------------------------   
          	  	    PwMotor =  (0.5*err_vel + integ_angl);  // was 0.22
          	  	    //PwMotor =  (0.22*err_vel + integ_angl);  // was 0.22   
          	  	     if (PwMotor > 1990)  PwMotor = 1990;    // was 990
          	  	     if (PwMotor < -1990) PwMotor = -1990;  
          	       
// ****************************************************************************************************         	  	 
                  if (flag_STOP)   PwMotor = 0;            // Emergency STOP Rotation	!!!!!!!!!!!!!!! 
                  if (enc_angl_gr > 18000) PwMotor = 0;    // Limitation +180 dgr
                  if (enc_angl_gr < -18000) PwMotor = 0;   // Limitatiom -180 dgr
// ****************************************************************************************************  
	SRU2(LOW, DAI_PB03_I);								   // 4kHz - event freq. to vibro-mode!	
			  		motorCTL(PwMotor,motor_angl);          // Motor Control Procedure
	SRU2(HIGH, DAI_PB03_I);		  		 
          	    } // end work 
//          	            	
// Current Angle Velocity calculation  4kHz freq. 
//               
                 angle = angle_sm;
                 angle_sm =0.0; 
                 vel_angle = 40*(angle - angle_old);                          
                 angle_old = angle;
//                 				             
            }  // end of decimation
           else {
           	     angle_sm += enc_angl_gr; // òî÷íî íå 4 ðàçà ñðàáîòàåò?
                } 
//                     		
//---------------------------------------------------------------------------------- 
      if (PWM_stat & PWM_STAT1)   // Pelt'e element control
       {
       	*pPWMGSTAT = PWM_stat;    // clear interrupt bit

         if (Peltier < 0) SRU(HIGH,DAI_PB16_I);
          else SRU(LOW,DAI_PB16_I);      	
        *pPWMAL1 = (unsigned int)(-1999 + abs(Peltier));   // middle of range
       } 
// ----------------------------------------------------------------------------------      
      if (PWM_stat & PWM_STAT2)  
       {  
       	*pPWMGSTAT = PWM_stat;   // clear interrupt bit
        *pPWMA2 = (unsigned int)(AA);   // AL2 -> pin X37        	// AH2 -> pin X38
        *pPWMB2 = (unsigned int)(BB);   // BL2 -> pin X39           // BH2 -> pin X7
       } 
// ----------------------------------------------------------------------------------     
	 if (PWM_stat & PWM_STAT3)  
       {
       	*pPWMGSTAT = PWM_stat;   // clear interrupt bit
        *pPWMA3 = (unsigned int)(CC);   // AL3 -> pin X5
                                 // BL3 -> pin X6
       } 
// ----------------------------------------------------------------------------------
/*                 cou_pwm++;       // 40kHz
        if (cou_pwm > 49)         // 199 200Hz event frequrncy
         { cou_pwm = 0;           // reset counter
//	         	        	
			   GetAsicData();	 // 769Hz	Get DATA ASIC			         						
//			 else       { GetTempData();}    // 769Hz    Get Temperature ASIC			        		
//				flag_T = !flag_T;			
         }
 */   
// ----------------------------------------------------------------------------------        
     SRU(LOW,DAI_PB12_I);	// ~~|__|~~  t = 40 ns
   	 asm("nop;");           // SOC pulse (Start ADCs Conversion)
   	 asm("nop;");
	 SRU(HIGH,DAI_PB12_I);     	  
}
//==========================================================================================
//******************************************************************************************
void write_UART(char *xmit, int len)
{
	int i;
//  
  for (i=0; i < len; i++)
   {      
    do {;} while ((*pUART0LSR & UARTTHRE) == 0); // Wait for the UART transmitter to be ready    	       
                   *pUART0THR = xmit[i];         // Transmit a byte
   }  
           while ((*pUART0LSR & UARTTEMT) == 0) {;}  // poll to ensure UART has completed the transfer 
// 
}
//
//++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
void wait(int cou) { int i,k; for (i=0;i<cou;i++) k = i*i+i;}                       //
//++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
//                     
void main(void)
{ int i;
//  set vector 0x13 
	*pPICR2 &= ~(0x3E0);  // Clear the area to the selected interrupt (P13I)
	*pPICR2 |= (0x13<<5); // Sets the UART0 receive interrupt (and vector 0x13)
//
//  set vector 0x18 (PWM) 
	*pPICR0 &= ~(0x1F); // Clear the area to the selected interrupt (P0I)
	*pPICR0 |= (0x18);  // Sets the PWM interrupt (vector 0x18)
//	
	initPLL(); 
// Temperature Chamber control	
// ======================================================================
	SRU2(HIGH, DPI_PBEN04_I);    // Enable DPI04 pin 24 as OUT (PWM1_AL0 out)
	SRU2(PWM1_AL_O, DPI_PB04_I); // PWM1_AL_O
// ======================================================================		
// Motor rotate control 	
//	PWM2 & PWM3 channels ---------------  SPIB for USB out
	SRU2(HIGH, DPI_PBEN11_I);     // pin 32 as OUT
	SRU2(PWM2_AL_O, DPI_PB11_I);  //     AL2				out X37 -->AL2  U
//	SRU2(HIGH, DPI_PBEN11_I);      // pin 32
//	SRU2(SPIB_MISO_O,DPI_PB11_I); // SPIB_MISO (mode slave) out X37 -->
//	
	SRU2(HIGH, DPI_PBEN12_I);     // pin 33 as OUT
	SRU2(PWM2_AH_O, DPI_PB12_I);  //     AH2				out X38 -->AH2 ~U
//	SRU2(LOW, DPI_PBEN12_I); 
//	SRU2(DPI_PB12_O,SPIB_DS_I); // SPIB ~CS (mode slave) input X38 <--
//  PWM3 channel ---------------
	SRU2(HIGH, DPI_PBEN13_I);     // pin 34 as OUT
	SRU2(PWM2_BL_O, DPI_PB13_I);  //     BL2				out X39 -->BL2
//	SRU2(LOW, DPI_PBEN13_I);
//	SRU2(DPI_PB13_O,SPIB_CLK_I);  // SPIB_CLK (mode slave)  input X39 <--   V
//+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++	
	SRU2(HIGH, DPI_PBEN06_I);     // pin 25 as OUT 
	SRU2(PWM2_BH_O, DPI_PB06_I);  //     BH2				out X7 -->BH2  ~V
	
	SRU2(HIGH, DPI_PBEN08_I);     // pin 27 as OUT 
	SRU2(PWM3_AL_O,DPI_PB08_I);   //     AL3				out X5 -->AL3   W	
		
	SRU2(HIGH, DPI_PBEN07_I);     // pin 28 as OUT 
	SRU2(PWM3_AH_O,DPI_PB07_I);   //     AH3				out X6 -->AH3  ~W      	
// =======================================================================
//	SRU(PCG_FSA_O, DAI_PB15_I);   // Assign PCG_FSA  out
//	SRU(PCG_CLKA_O, DAI_PB16_I);  // Assign PCG_CLKA out
// =======================================================================
	SRU(HIGH, PBEN09_I);		  // Enable DAI_P09 out
	SRU(HIGH, PBEN03_I);		  // Enable DAI_P03 out
	SRU(HIGH, PBEN11_I);		  // Enable DAI_P11 out
//	
	SRU(LOW, PBEN15_I);		      // Enable DAI_P15 as input (amp. protection)
	SRU(HIGH, PBEN16_I);		  // Enable DAI_P16 out
//	 
	SRU(HIGH, PBEN04_I);          // PBEN04_I ~CS0 -> select ASIC
	
//	
//	SRU(HIGH, PBEN20_I);          //
//	SRU(LOW, PBEN10_I);           //
	SRU(LOW, PBEN09_I);
//	
	SRU(HIGH, PBEN13_I);  // Enable DAI13 pin 40 as OUT (Clk23)	
	SRU(HIGH, PBEN14_I);  // Enable DAI14 pin 58 as OUT (FS23)
//	SRU(HIGH, PBEN20_I);  // Enable DAI20 pin  as OUT (FS23)
	SRU(HIGH, PBEN17_I);  // Enable DAI17 X19 as OUT
	SRU(LOW, DAI_PB17_I);
	
//	
	SRU(LOW, PBEN05_I);  // Enable DAI05 pin 49 as Data input (Temperature)
//SPORT4   for USB usege
//	SRU(DAI_PB09_O,SPORT4_CLK_I);
//	SRU(DAI_PB10_O,SPORT4_FS_I);
//	SRU(SPORT4_DA_O, DAI_PB20_I); 
//	 	
//SPORT3   for make external clock and frame synchronization
    SRU(SPORT3_CLK_O,DAI_PB13_I);    	
	SRU(SPORT3_FS_O, DAI_PB20_I);//DAI_PB14_I
//SPORT2 for Temperature Data input	
	SRU(SPORT3_CLK_O,SPORT2_CLK_I);
	SRU(SPORT3_FS_O,SPORT2_FS_I);
	SRU(DAI_PB05_O,SPORT2_DA_I );
//========================================================		
//SPORT1 for Data input from all ASICs 
	SRU(SPORT1_CLK_O,DAI_PB07_I);		   
	SRU(SPORT1_FS_O, DAI_PB08_I);	
//SPORT1 for make external clock and frame synchronization	
	SRU(SPORT1_CLK_O,SPORT0_CLK_I);
    SRU(SPORT1_FS_O,SPORT0_FS_I);	
//========================================================	
	SRU(HIGH,PBEN07_I);	
	SRU(HIGH,PBEN08_I);	
//  ~SCNV start ADC conversion (two channel of AD7688)	
 	SRU(HIGH,PBEN12_I);	// 
 	SRU(HIGH,DAI_PB12_I);
// 	
 	*pSPIFLG  = 0x0;
 	SRU(HIGH,DPI_PB05_I); // disable autoselect SPI high (SPI_FLAG0 - use only to first loader)
// 	SRU(LOW, PBEN10_I);   // DAI_P10 to in (Data int.)
//	
//	SRU(SPORT0_DA_O, DAI_PB10_I); 	
// 	SRU(DAI_PB10_O, DAI_INT_22_I); // connect DAIPB10 (pin 51) to int 22 			  	
//	*pSRU_EXT_MISCB = 0x00000009; // set DAI_PB10_O as a sourse of 22-interrupt
//	*pDAI_IMASK_RE   = 0x00400000; // unmask 22-intterrupt 		
//
	sysreg_write(sysreg_MODE1, IRPTEN | NESTM); // Enable global interrupt and Nestling
    for (i=0; i<16; i++) asm("nop;"); 
//	                            IRQ1   SPI_HI  TIM_0  SPORT1  SPORT3  PWM        coreTim  IRQ0 
	sysreg_write(sysreg_IMASK,  IRQ1I | P1I | P6I |  P2I |  P3I  | P4I  | P0I | P7I ); //| TMZLI  | IRQ0I
//
	wait(0xff);
	imask = sysreg_read(sysreg_IMASK);
//	
	sysreg_write(sysreg_LIRPTL, P10IMSK | P13IMSK  | P6IMSK ); // P18IMSK | P7IMSK  | P9IMSK| P8IMSK 
//                                TIM1     UART      SPORT0       SPI_lo|w  SPORT2            SPORT4 
	wait(0xff);
	lirptl = sysreg_read(sysreg_LIRPTL);
//	
	sysreg_write(sysreg_MODE2,IRQ1E | IRQ0E); // Enable IRQ1 edge sensitive
	for (i=0; i<16; i++) asm("nop;"); 
//	
	*pSYSCTL |= PWMONDPIEN | PWM1EN | PWM2EN | PWM3EN | IRQ1EN ;	//| IRQ0EN| PWM0EN enable to use DPI to PWM and IRQ1
    for (i=0; i<16; i++) asm("nop;"); 	
//		
//----------------------------------------------------------------------
	*pUART0LCR=0;	
    *pUART0IER   = UARTRBFIE;    // enables UART0 only receive interrupt
//  	
	init_DPI();
	init_UART();
    init_Timers();
    init_Timers_IRQ();	  
//  
//	interrupt(SIG_P18,  spiB_ISR);    // disable now!
	interrupt(SIG_IRQ1, IRQ1_ISR);    // Assign IRQ1 signal to IRQ1_ISR proc.
//	interrupt(SIG_IRQ0, IRQ0_ISR);    // Assign IRQ1 signal to IRQ1_ISR proc.
	interrupt(SIG_P1, spi_ISR);       // Assign SPI Interrupt to ISR routine 	
//	interrupt(SIG_P0, DAIPB10_ISR);   // Assign hi-pri DAI int to DAI_PB10_ISR   
	interrupt(SIG_P13, UART_ISR);     // assign signal to UART_ISR
//	interrupt(SIG_TMZ0, TMZLI_ISR);   // assign Core timer int. to TMZLI_ISR
	interrupt(SIG_P2, tim0_ISR);      // assign signal to Timer0_ISR
	interrupt(SIG_P10,tim1_ISR);      // assign signal to Timer1_ISR
	interrupt(SIG_P0, PWM_ISR);       // assing signal to PWM_ISR
//
	interrupt(SIG_SP1, Sport1_ISR);   // assign signal to Sport1
	interrupt(SIG_SP3, Sport3_ISR);   // assign signal to Sport3
//	interrupt(SIG_SP4, Sport4_ISR);   // assign ISR to SPORT4 ISR-signal
//
	initPWM();                        // Start PWM
//    initPCGA(PCG_W);
//    write_UART(strLoad,strlen(strLoad)); // "ADSP-21489 Started !..." message Request data exchange
//
	*pTMSTAT =  TIM0EN | TIM1EN;	// Start timer0 and timer1 	
//	Core timer parameters
//	timer_set(6400,1); //50000Hz   12800000 = 25Hz  100000 0x834(period, count) 152 kHz
//    timer_on();            // start Core timer
//  =================================================================
//
	SRU(HIGH,DAI_PB03_I); //  X28 indication
	SRU(LOW,DAI_PB11_I);  //  High - disable motor!
//
	initUARTDMA_RX();     // initialize UART receive
//
//	USB_SPIB();   	  // Start USB-SPI with chain mode (continuously)
//				
   while(1)
      {
   	 asm("idle;");
      }   
}
