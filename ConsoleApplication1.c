/*
    расположение: C:\Users\al-zi\source\repos\ConsoleApplication1\ConsoleApplication1
	расположение exe (!!!): C:\Users\al-zi\source\repos\ConsoleApplication1\x64\Debug
	или: C:\Users\al-zi\source\repos\ConsoleApplication1\x64\Debug\ConsoleApplication1.exe
	или: C:\Users\al-zi\source\repos\ConsoleApplication1\x64\Release\ConsoleApplication1.exe
*/

#include "ConsoleApplication1.h"

int main(void) 
{
    /* Инициализация переменных */ 
    Config_t Config;
        Config.COM_num = 0;
        Config.exit_flag = FALSE;
        Config.time_change_flag = 0.5;
        Config.Vrange_flag = 16;
        Config.update_flag = UPDATE_PERIOD;
    char  buf[24];
    float Vol = -1;
    PORT COM;
    OVERLAPPED    ovrlapp;
    memset(&ovrlapp, 0, sizeof(ovrlapp));
    ovrlapp.hEvent = CreateEvent(NULL, FALSE, FALSE, NULL);

    /* Подготовка к работе */
    system("cls");
    Set_window_params(115, 28);
    output_text();
    COM = Input_COM(&Config);
    draw_indicator(Config.Vrange_flag / 16);

    /* Обработка команд и приём данных измерений */
    while (!Config.exit_flag)
    {
        if (gets_async_text(buf, sizeof(buf)) != NULL)
            check_command(buf, &Config);
           
        if (Config.update_flag)
            COM = execute_command(COM, &Config, &ovrlapp);
  
        Vol = Recieve_UART(COM, &ovrlapp);

        redraw_arrow(Vol / Config.Vrange_flag);
    }

    /* Завершение работы */
    ClosePort(COM);
    return_scrollbar(); // на случай запуска из командной строки
    return 0;
}

/*  Получение напряжения
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
float Recieve_UART(PORT COM, OVERLAPPED* ovrlapp)
{
    HWND handle = GetConsoleWindow();
    HDC  hdc = GetDC(handle);
    SetTextAlign(hdc, TA_LEFT);
    SetBkColor(hdc, BLACK);

    float   Vol = -1;
    uint8_t buf_size = 6;
    uint8_t recive_str[7];
    DWORD   sz_received_data;
    static  uint16_t time_ms = 0;

    // bResult = ReadFile(hFile, &recive_str, buf_size,
    //&nBytesRead, NULL);
    // Проверяем не конец ли это файла. 
    //if (bResult && nBytesRead == 0, )
    //{
        // Мы достигли конца файла. 
    //}
    ReadFile(COM, &recive_str, buf_size, &sz_received_data, ovrlapp);

    if (WaitForSingleObject(ovrlapp->hEvent, 100) == WAIT_OBJECT_0)
    {   // если в буфер ничего не поступило, то функция будет возвращать TRUE, т.е. мы будем работать с теми же значениями
        GetOverlappedResult(COM, ovrlapp, &sz_received_data, FALSE);

        if (sz_received_data >= 6) //  возможно, проверка не нужна
        {
            time_ms = 0;
            uint8_t i;
            for (i = 0; recive_str[i] != 'V'; i++);
            Vol = (float)((recive_str[i + 1] << 8) | recive_str[i + 2]) / 1000;
            char msg[11];
            snprintf(msg, sizeof(msg), "%.3f V  ", Vol);
            SetTextColor(hdc, GREY);
            TextOutA(hdc, 8 * 9, 16 * 8, msg, sizeof(msg)); // поменял strlrn на sizeof

            SetTextColor(hdc, GREEN);
            TextOutA(hdc, 8 * 18, 16 * 10, "Ok ", 3);
            PurgeComm(COM, PURGE_RXCLEAR); // если у нас будут накапливаться сообщения, то это может привести к сбою
        }
    }
    else
    {
        if (time_ms > 5000)
        {
            SetTextColor(hdc, RED);
            TextOutA(hdc, 8 * 18, 16 * 10, "Off", 3); // можно просто printf использовать
        }
        else time_ms +=100;
    }
    ReleaseDC(handle, hdc);    // Освобождаем контекст рисования
    return Vol;
}

/*  Стрелочный индикатор
    -----------------------------------------------------------------------------------------------------------------------------------------------
*/
void draw_indicator(uint8_t k_range)
{
    Sleep(25);
    HWND handle = GetConsoleWindow();
    HDC  hdc = GetDC(handle);

    const COORD    center = { 490, 180 };
    const uint8_t  scale_len = 150;

    HPEN p01 = CreatePen(PS_SOLID, 3, RED); // Создаем красное перо
    SelectObject(hdc, p01);  // Заносим перо в контекст рисования
    SelectObject(hdc, GetStockObject(WHITE_BRUSH));

    /* Рисуем каркас */
    BeginPath(hdc);
    MoveToEx(hdc, center.X, center.Y, NULL);
    AngleArc(hdc, center.X, center.Y, scale_len / 5, 15, 150); 
    EndPath(hdc);
    StrokeAndFillPath(hdc);

    BeginPath(hdc);
    MoveToEx(hdc, center.X, center.Y, NULL);
    AngleArc(hdc, center.X, center.Y, scale_len + 11, 15, 150); 
    LineTo(hdc, center.X, center.Y);
    AngleArc(hdc, center.X, center.Y, scale_len - 19, 15, 150); 
    EndPath(hdc);
    StrokeAndFillPath(hdc);

    /* Подписи оси */
    char    AxisText[17][3];
    uint8_t size, i = 0;
    float   COS, SIN, ang;
    SetTextAlign(hdc, TA_CENTER);

    for (ang = (float) (7 * PI / 6); ang <= (float)11.1 * PI / 6; ang += (float) (PI / 24), i++)
    {
        COS = cosf(ang);
        SIN = sinf(ang);
        MoveToEx(hdc, 
            center.X + (int)round((scale_len - 20) * COS), 
            center.Y + (int)round((scale_len - 20) * SIN), 
            NULL);
        LineTo(hdc, 
            center.X + (int)round((scale_len - 14) * COS), 
            center.Y + (int)round((scale_len - 14) * SIN));

        snprintf(AxisText[i], sizeof(AxisText[i]), "%u", i * k_range);
        size = (i * k_range < 10) ? 1 : 2;
        TextOutA(hdc, 
            center.X + (int)round(scale_len * COS), 
            center.Y - 4 + (int)round(scale_len * SIN), 
            (AxisText[i]), size);
    }
    ang = (float) (11.2 * PI / 6);
    COS = cosf(ang);
    SIN = sinf(ang);
    TextOutA(hdc, 
        center.X + (int)round(scale_len * COS), 
        center.Y + (int)round(scale_len * SIN), 
        "V", 1);

    SelectObject(hdc, GetStockObject(NULL_PEN));
    DeleteObject(p01);
    ReleaseDC(handle, hdc);
}

/*  Перерисовка стрелки
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
void redraw_arrow(float voltage_norm)
{
    static float voltage_prev = -1;
    if ((voltage_norm >= 0) && (voltage_norm <= 1) && (voltage_norm != voltage_prev))
    {
        HWND handle = GetConsoleWindow();
        HDC  hdc = GetDC(handle);

        /* Закрашиваем прежнюю стрелку */
        HPEN p1 = CreatePen(PS_SOLID, 3, BLACK);
        SelectObject(hdc, p1);
        
        draw_arrow(voltage_prev, hdc);

        /* Расчёты */
        voltage_norm = (float) (2 * PI / 3) * voltage_norm + (7 * PI / 6);

        /* Рисуем новую стрелку */
        HPEN p2 = CreatePen(PS_SOLID, 2, RED);
        SelectObject(hdc, p2);

        draw_arrow(voltage_norm, hdc);
  
        voltage_prev = voltage_norm;

        SelectObject(hdc, GetStockObject(NULL_PEN));
        DeleteObject(p1);
        DeleteObject(p2);
        ReleaseDC(handle, hdc);
    }  
}

/*  Стрелка
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
void draw_arrow(float voltage_norm, HDC hdc)
{
    const  uint8_t  scale_len = 150;
    const  uint8_t  arrow_len = 15;
    const  COORD    center = { 490, 180 };

    int16_t cos_x = (int16_t)round((scale_len - 23) * cosf(voltage_norm));
    int16_t sin_y = (int16_t)round((scale_len - 23) * sinf(voltage_norm));

    MoveToEx(hdc, center.X + cos_x / 4, center.Y + sin_y / 4, NULL);
    LineTo(hdc, center.X + cos_x, center.Y + sin_y);

    LineTo(hdc,
        center.X + cos_x + (int)round(-arrow_len * cosf(voltage_norm + (float)PI / 9)),
        center.Y + sin_y + (int)round(arrow_len * sinf(-voltage_norm - (float)PI / 9)));
    MoveToEx(hdc, center.X + cos_x, center.Y + sin_y, NULL);
    LineTo(hdc,
        center.X + cos_x + (int)round(-arrow_len * cosf(voltage_norm - (float) PI / 9)),
        center.Y + sin_y + (int)round(-arrow_len * sinf(voltage_norm - (float)PI / 9)));
}

/*  Асинхронное чтение
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
char* gets_async_text(char* buf, uint16_t size)
{
    HANDLE hConsole = GetStdHandle(STD_INPUT_HANDLE);

    INPUT_RECORD InputRecord[32];
    DWORD i, NumOfEvents = 0;
    DWORD Length = 32;
    char* pointer = NULL;

    if (PeekConsoleInput(hConsole, InputRecord, Length, &NumOfEvents))
    {    
        for (i = 0; i < NumOfEvents; ++i)
        {
            if (InputRecord[i].EventType == KEY_EVENT)
            {
                if (InputRecord[i].Event.KeyEvent.bKeyDown)
                {
                    gotoxy(29, 14);
                    puts("(Pause)");
                    gotoxy(10, 14);
                    fseek(stdin, 0, SEEK_END);
                    pointer = fgets(buf, size, stdin);
                    fflush(stdin);
                    gotoxy(10, 14);
                    clrallafter();
                    break;
                }
            }
        }
    }
    return pointer;
}

/*  Команды
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
void check_command(char* buf, Config_t* Config)
{      
    const char* period_msg = "period";
    const char* range_msg = "range";
    const char* connect_msg = "connect";
    const char* exit_msg = "exit";

    if (strncmp(buf, range_msg, 5) == 0)
    {
        uint8_t result = atoi(buf + 6); 
        //printf("__range change %u", result);
        if ((result == 32) || (result == 16))
        {
            Config->Vrange_flag = result;
            Config->update_flag = UPDATE_RANGE;
        }
    }
    else if (strncmp(buf, period_msg, 6) == 0)
    {
        float result = (float)atof(buf + 7);
        //printf("\n\n\n\n\nperiod_mode change to %.1f to %s", Config->time_change_flag, buf + 7);
        if ((result >= 0.5) && (result <= 5))
        {
            Config->time_change_flag = result;
            Config->update_flag = UPDATE_PERIOD;
        }
    }
    else if (strncmp(buf, connect_msg, 7) == 0) // работает
    {
        uint8_t result = atoi(buf + 8); // считывает цифры до перой не цифры
        if (result)
        {
            Config->COM_num = result;
            //printf("___connect to %i to %s F", Config->COM_num, buf + 8);
            Config->update_flag = UPDATE_COM_PORT;
        }
    }
    else if (strncmp(buf, exit_msg, 2) == 0)
    {
        Config->exit_flag = TRUE;
    }
    else
    {
        HWND handle = GetConsoleWindow();
        MessageBoxA(handle,
            "Invalid command",
            "Console app (2023, Zinkevich)",
            MB_ICONEXCLAMATION | MB_OK); // MB_ICONEXCLAMATION - то, что восклицательный знак нарисован
    }
}
 
/*  Отправка команд
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
PORT execute_command(PORT COM, Config_t* Config, OVERLAPPED* ovrlapp)
{
    if (Config->update_flag == UPDATE_COM_PORT)
    {
        PORT temp = OpenPortOverlapped(Config->COM_num);
        if (temp != FALSE)
        {
            //printf("\n\n__connect DONE %u_/___", Config->COM_num);
            ClosePort(COM); // лучше, но всё ещё вылетает при много кратком переключении
            COM = temp;
            COM_info(COM, Config->COM_num);
            draw_indicator(Config->Vrange_flag / 16);
        }
        else
        {
            HWND handle = GetConsoleWindow();
            MessageBoxA(handle,
                "Cannot connect",
                "Console app (2023, Zinkevich)",
                MB_ICONEXCLAMATION | MB_OK);
        }
        Config->update_flag = NO_UPDATE;
    }
    else if (WaitForSingleObject(ovrlapp->hEvent, 0) == WAIT_OBJECT_0)
    {
       switch (Config->update_flag)
       {
            case UPDATE_RANGE:
            {
                draw_indicator(Config->Vrange_flag / 16);
                uint8_t Msg[3] = { 0x02, Config->Vrange_flag / 16, 0x00 };
                Msg[2] = get_crc8(Msg, 2);
                WriteFile(COM, Msg, sizeof(Msg), NULL, ovrlapp);
                //printf("\n\nrange ch DONE %u size %i %i", Config->Vrange_flag / 16, strlen(Msg), sizeof(Msg));
                break;
            }
            case UPDATE_PERIOD:
            {
                uint8_t Msg[3] = { 0x03, (uint8_t)round(Config->time_change_flag * 20), 0x00 };
                Msg[2] = get_crc8(Msg, 2);
                WriteFile(COM, Msg, sizeof(Msg), NULL, ovrlapp);
                //printf("\n\nCRC8 %u period change DONE %u work? %u", Msg[2], Msg[1], (uint8_t)round(Config->time_change_flag * 2));
                break;
            }
       }
       Config->update_flag = NO_UPDATE;
    }
    return COM; 
}


/*  Текст, которые не меняется
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
void output_text(void)
{
    gotoxy(85, 2);
    printf("\33[1K\r");
    gotoxy(0, 2);
    set_display_atrib(BLINK);
    puts("Command list:\n");
    resetcolor();

    puts(" 1 - period X.X (where X.X - 0.5...5 sec)");
    puts(" 2 - connect X  (where X - number of COM)");
    puts(" 3 - range XX   (where XX - 16 or 32 V)");
    puts(" 4 - exit");

    gotoxy(0, 9);
    puts("Voltage:");
    gotoxy(0, 11);
    puts("Connection state:");

    uint8_t X = 85;
    gotoxy(X, 2);
    printf("Current port:");
    gotoxy(X, 4);
    printf("PortBoudRate:");
    gotoxy(X, 6);
    printf("PortDataBits:");
    gotoxy(X, 8);
    printf("PortStopBits:");
    gotoxy(X, 10);
    printf("PortParity:");

    gotoxy(10, 14);
}

/*  Ввод номера СОМ порта
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
PORT Input_COM(Config_t* Config)
{
    HWND    handle = GetConsoleWindow();

    PORT    COM;
    uint8_t buf[5];
    uint8_t ans = IDYES;
    uint32_t Num = 0; //

    gotoxy(0, 14);
    puts("Input COM number:");

    do
    {
        fseek(stdin, 0, SEEK_END);
        gotoxy(19, 14);
        //fgets(buf, 5, stdin);
        scanf_s("%u", &Num);

        //if (Num != 0)
        //{
            gotoxy(19, 14);
            clrallafter(); //printf("faf = %u", Num);
            //Num = atoi(buf);
            COM = OpenPortOverlapped(Num);
            //COM = OpenPortOverlapped(Num);
            //if (COM == INVALID_HANDLE_VALUE)
            if (COM != FALSE)
            {
                Config->COM_num = Num;
                COM_info(COM, Config->COM_num);
            }
            else
            {
                ans = MessageBoxA(handle,
                    "Cannot coonect!\nTry again or exit?",
                    "Console app (2023, Zinkevich)",
                    MB_ICONEXCLAMATION | MB_YESNO);
                if (ans != IDYES) exit(-2);
            }
        //}
    } while (COM == FALSE);

    gotoxy(0, 14);
    clrallafter();
    puts("Command:");
    gotoxy(10, 14);
    return COM;
}

/*  Вывод информации о СОМ порте
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
void COM_info(PORT COM, uint8_t num)
{
    uint8_t X = 99;

    gotoxy(X, 2);
    printf("COM%u ", num);
    gotoxy(X, 4);
    printf("%i ", GetPortBoudRate(COM));
    gotoxy(X, 6);
    printf("%i ", GetPortDataBits(COM));
    gotoxy(X, 8);
    if (GetPortStopBits(COM) == 0) printf("STOP_BITS_ONE ");
    gotoxy(X, 10);
    if (GetPortStopBits(COM) == 0) printf("NOPARITY ");
    gotoxy(10, 14);
}

/*  Настройка окна
    ---------------------------------------------------------------------------------------------------------------------------------------------
*/
BOOL Set_window_params(SHORT width, SHORT height)
{
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    COORD NewSize = { width , height }; // сначала столбцы, потом строки)
    SMALL_RECT DisplayArea = { 0, 0, width - 1, height - 1 };
    
    SetConsoleTitleA("Console app (2023, Zinkevich)");

    if (!SetConsoleWindowInfo(hConsole, TRUE, &DisplayArea)) // изменение размера окна консоли
        return FALSE;
    if (!SetConsoleScreenBufferSize(hConsole, NewSize)) // изменение размера буфера консоли
        return FALSE;

    return TRUE;
}

/* Возвращение консоли прежнего вида
    -----------------------------------------------------------------------------------------------------------------------------------------------
*/
void return_scrollbar(void)
{
    CONSOLE_SCREEN_BUFFER_INFO scrBuffInfo;
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    GetConsoleScreenBufferInfo(hConsole, &scrBuffInfo);

    COORD new_scr_buff_sz;
    new_scr_buff_sz.X = scrBuffInfo.dwSize.X;
    new_scr_buff_sz.Y = ++scrBuffInfo.dwSize.Y;

    SetConsoleScreenBufferSize(hConsole, new_scr_buff_sz);

    gotoxy(0, 24);
}
