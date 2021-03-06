'''
helper functions to make litex RemoteClient easier to use
'''
from numpy import *


def getId(r):
    ''' return litex soc ID string '''
    s = ""
    for i in range(64):
        temp = r.read(r.bases.identifier_mem + i * 4)
        if temp == 0:
            break
        s += chr(temp & 0xFF)
    return s


def hd(dat, pad_width=1, word_width=None):
    ''' print a hex-dump, word_width in bytes '''
    if word_width is None:
        word_width = pad_width
    for i, d in enumerate(dat):
        if i % 8 == 0 and len(dat) > 8:
            print('\n{:04x}: '.format(i * word_width), end='')
        print('{:0{ww}x} '.format(d, ww=pad_width * 2), end='')
    print()


def big_read(r, addr, length, chunk_size=255):
    """
    read data of arbitrary length in chunks
    r: litex RemoteClient object
    addr: start address in [bytes], should be 32 bit aligned
    length: number of 32 bit words to read
    chunk_size: how many words to read in one Etherbone transaction
    """
    dats = []
    while length > 0:
        temp = r.read(addr, min(chunk_size, length))
        dats.append(temp)
        addr += len(temp) * 4
        length -= len(temp)
    # return hstack(dats)
    return [i for dat in dats for i in dat]


def big_write(r, addr, datas, chunk_size=255):
    '''
    write large amount of data to litex server in chunks

    r: a litex RemoteClient object
    addr: start address in [bytes]
    datas: list or numpy array of dtype uint32
    chunk_size: how many words to write in one Etherbone transaction
    '''
    datas = array(datas, dtype=uint32)
    s_index = 0
    while True:
        dat = datas[s_index: s_index + chunk_size]
        if len(dat) <= 0:
            break
#         print("****", hex(addr))
#         hd(dat, 4)
        r.write(addr, dat.tolist())
        addr += 4 * len(dat)
        s_index += chunk_size


def setSamples(r, samples):
    '''
    Write sample memory of arbitrary waveform generator

    r: a litex RemoteClient object
    samples: numpy array of dtype int16
             len(samples) will be clipped to the next multiple of 16
    '''
    N_MEM = 8  # Number of block rams
    N_SAMPLES = 16  # parallel samples / dsp clock cycle

    # signed 16 bit samples in natural order
    samples = array(samples, dtype=int16)
    samples *= -1

    # pack 2 x signed 16 bit samples into one unsigned 32 bit memory word
    s_u8 = samples.tobytes()
    s_u32 = frombuffer(s_u8, dtype=uint32)

    for n in range(N_MEM):
        mem = getattr(r.mems, f'm0_n{n}')
        s = s_u32[n::N_MEM]
#         hd(s, 4)
        big_write(r, mem.base, s)

    r.regs.sample_gen_max_ind.write(len(samples) // N_SAMPLES - 1)
