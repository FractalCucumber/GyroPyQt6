// ConsoleApplication1.cpp : Этот файл содержит функцию "main". Здесь начинается и заканчивается выполнение программы.
//

#include <iostream>
#include "../../CRC8.h"
#include "../../CSerialPort.h"

// C:\Users\zinkevichav\source\repos\ConsoleApplication1\x64\Debug
// C:/Users/zinkevichav/source/repos/ConsoleApplication1/x64/Release
// cmd: C:\Users\zinkevichav\source\repos\ConsoleApplication1\x64\Release\ConsoleApplication1 SetVel
// cmd: C:\Users\zinkevichav\source\repos\ConsoleApplication1\x64\Debug\ConsoleApplication1 SetVel
#define     LEN = 5;


int main(int argc, char* argv[])
{
    const char* str[] = {
        "Vel",   // 0
        "Angle",     // 1
        "Stop",     // 2
    };
    //std::cout << "\nLength of array = " << (sizeof(str));
    //std::cout << "\nLength of array = " << sizeof(*str);
    int len = (int) (sizeof(str) / sizeof(*str));
    std::cout << "\nlen of array = " << len;
    //std::cout << "\nLength of array = " << (sizeof(str) / sizeof(*str));
    //const char* str2[5];
    //str2[0] = "Vel"; //str2[1] = "Angle"; //str2[2] = "Angle2"; //str2[3] = "Angle3"; //str2[4] = "Angle4";
    //for (int i = 0; i < argc; i++)
    uint8_t message[] = { 0x4D, 0x00, 0x01, 0x00, 0x64, 0x00, 0x00, 0x00 };
    const uint8_t stop_message[] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    int COM_num = 3;
    PORT COM = OpenPort(COM_num);
    //std::cout << std::endl << (COM == NULL);
    //std::cout << std::endl << (COM == INVALID_HANDLE_VALUE);
    //std::cout << std::endl << (COM == 0);
    //std::cout << std::endl << ((int)COM > 0);
    //std::cout << std::endl << ((int)COM == FALSE);
    //std::cout << std::endl << (COM == FALSE);
    if (COM == FALSE) 
    {
        std::cerr << "Failed to get COM port." << std::endl;
        std::cout << ClosePort(COM);
        return -1;
    }
    std::cout << std::endl << "Connected";

    DCB dcbSerialParams = { 0 };
    dcbSerialParams.DCBlength = sizeof(dcbSerialParams);
    if (!GetCommState(COM, &dcbSerialParams)) {
        std::cerr << "Failed to get COM port state." << std::endl;
        CloseHandle(COM);
        return -1;
    }
    dcbSerialParams.BaudRate = 921600;
    dcbSerialParams.ByteSize = 8;
    dcbSerialParams.StopBits = ONESTOPBIT;
    dcbSerialParams.Parity = NOPARITY;
    if (!SetCommState(COM, &dcbSerialParams)) {
        std::cerr << "Failed to set COM port state." << std::endl;
        CloseHandle(COM);
        return -1;
    }

    //SetPortDataBits(COM, 8);
    //SetPortBoudRate(COM, CBR_115200 * 8); // 921600
    //SetPortStopBits(COM, ONESTOPBIT);
    //SetPortParity(COM, NOPARITY);
    //printf("\nBoudRate=%i ", GetPortBoudRate(COM));
    //printf("\n%i ", GetPortDataBits(COM));
    //Sleep(50);
    //for (int i = 0; i < 2; i++)
    //{
    int i = 0;
    std::cout << std::endl << "argc: " << argc << "\n";
    std::cout << std::endl << "argv 0: " << (argv[i]) << ", argv 0: " << atoi(argv[i]);
    std::cout << std::endl << "argv 1: " << (argv[i + 1]) << ", argv 1: " << atoi(argv[i + 1]);
    //std::cout << "\n argv 2: " << (argv[i + 2]) << ", argv 2: " << atoi(argv[i + 2]);
    i = 1;
    //if ((argc == 2) && (strncmp(argv[i], "Stop", 4) == 0))
    if (strncmp(argv[i], "Stop", 4) == 0)
    {
        std::cout << "\nstop ";
        WriteFile(COM, stop_message, sizeof(stop_message), NULL, NULL);
    }
    if ((argc >= 3) && (strncmp(argv[i], "Set", 3) == 0))
    {
        std::cout << "\nSet command\n";
        std::cout << argv[i]+3;
        //std::stoi("dd") // atoi
        for (int j = 0; j < len; j++) // тот же цикл для get
        {
            std::cout << "\nj:" << j << " str:" << str[i] << " argv[i]+3:" << (argv[i] + 3) << " compare:" << (strcmp(argv[i] + 3, str[j]) == 0);
            //if ((strncmp(argv[i] + 3, str[i], 3) == 0))
            if ((strcmp(argv[i]+3, str[j]) == 0))
            {
                //std::cout << argv[i + 1];
                int freq = atoi(argv[i + 1]);
                std::cout << "\natoi: " << freq;
                std::cout << "\nSet cmd: " << (argv[i] + 1);
                message[2] = freq & 0xff;
                message[2] = freq & 0xff;
                if (argc > 3) 
                {
                    int amp = atoi(argv[i + 2]);
                    message[4] = amp & 0xff;
                    message[5] = (amp >> 8) & 0xff;
                    //std::cout << "\n message: " << (char)y1;
                    WriteFile(COM, message, sizeof(message), NULL, NULL);
                }
                //Sleep(50);
                break;
            }
        }
        //std::cout << "\nSet command" << (argv[i] + 3);
    }
    else if ((argc > 1) && (strncmp(argv[i], "Get", 3) == 0))
    {
        std::cout << "\nGet command";
    }
    std::cout << '\n' + (char)i + '\0';
    //}
    std::cout << ClosePort(COM);
    return 0;

    //std::cout << "\nHello World!\n"; //

    //PORT COM2 = OpenPort(4);
    //std::cout << COM; //

    //WriteFile(COM, y1, sizeof(y1), NULL, NULL);
    //char y2[] = "01234567";
    //SendData(COM, y2);
    //char resieve[10];
    //ReciveData(COM2, resieve, 12);
    //std::cout << "\nFrom port: " << resieve;
    //std::cout << ClosePort(COM2);
    //std::cout << "\nWorld end!\n"; //
    //return 0;
}

// Запуск программы: CTRL+F5 или меню "Отладка" > "Запуск без отладки"
// Отладка программы: F5 или меню "Отладка" > "Запустить отладку"

// Советы по началу работы 
//   1. В окне обозревателя решений можно добавлять файлы и управлять ими.
//   2. В окне Team Explorer можно подключиться к системе управления версиями.
//   3. В окне "Выходные данные" можно просматривать выходные данные сборки и другие сообщения.
//   4. В окне "Список ошибок" можно просматривать ошибки.
//   5. Последовательно выберите пункты меню "Проект" > "Добавить новый элемент", чтобы создать файлы кода, или "Проект" > "Добавить существующий элемент", чтобы добавить в проект существующие файлы кода.
//   6. Чтобы снова открыть этот проект позже, выберите пункты меню "Файл" > "Открыть" > "Проект" и выберите SLN-файл.
