#ifndef INC_CRC8_H_
#define INC_CRC8_H_

#include <stdint.h>

#define CRC8_INIT_VALUE		0xfa
#define CRC8_END_VALUE		0x17

uint8_t get_crc8(uint8_t *buffer, uint8_t size);

#endif /* INC_CRC8_H_ */
