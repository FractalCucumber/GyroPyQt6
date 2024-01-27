
#include <stdio.h>
#include <windows.h>
#include <math.h>
#include "CSerialPort.h"
#include "CRC8.h"


#define PI 3.14159265358979323846

#define RED   RGB(255, 0, 0)
#define BLACK RGB(13, 12, 13)
#define GREEN RGB(0, 255, 0)
#define GREY  RGB(180, 180, 180)

typedef enum
{
	NO_UPDATE,
	UPDATE_RANGE,
	UPDATE_PERIOD,
	UPDATE_COM_PORT
} eUpdate_t; // название надо придумать

typedef struct
{
	uint8_t 	Vrange_flag;
	float		time_change_flag;
	uint8_t		COM_num;
	eUpdate_t	update_flag;
	BOOL		exit_flag;
} Config_t;

BOOL Set_window_params(SHORT width, SHORT height);
void output_text(void);
void COM_info(PORT COM, uint8_t num);
void return_scrollbar(void);
PORT Input_COM(Config_t* Config);
char* gets_async_text(char* buf, uint16_t size);
void check_command(char* buf, Config_t* Config);
PORT execute_command(PORT COM, Config_t* Config, OVERLAPPED* ovrlapp);
float Recieve_UART(PORT COM, OVERLAPPED* ovrlapp);
void redraw_arrow(float voltage_norm);
void draw_arrow(float voltage_norm, HDC hdc);
void draw_indicator(uint8_t k_range);

/* ESC-последовательности */
#define ESC "\033"

#define home() 							printf(ESC "[H") // Move cursor to the indicated row, column (origin at 1,1)
#define clrscr()						printf(ESC "[2J") // lear the screen, move to (1,1)
#define clrallafter()					printf(ESC "[0J") // очищение справа от курсора до конца экрана
#define gotoxy(x,y)						printf(ESC "[%d;%dH", y, x)
#define visible_cursor()				printf(ESC "[?251")
#define resetcolor()					printf(ESC "[0m")
#define set_display_atrib(color) 		printf(ESC "[%dm",color)
#define clrline()						printf(ESC "[K") // очищение справа от курсора

#define RESET 		0
#define BRIGHT 		1
#define DIM			2
#define UNDERSCORE	3
#define BLINK		4
#define REVERSE		5
#define HIDDEN		6

// Foreground Colours (text)
#define F_BLACK 	30
#define F_RED		31
#define F_GREEN		32
#define F_YELLOW	33
#define F_BLUE		34
#define F_MAGENTA 	35
#define F_CYAN		36
#define F_WHITE		37

// Background Colours
#define B_BLACK 	40
#define B_RED		41
#define B_GREEN		42
#define B_YELLOW	44
#define B_BLUE		44
#define B_MAGENTA 	45
#define B_CYAN		46
#define B_WHITE		47