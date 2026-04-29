#!/usr/bin/env python3
# 
# Seismophile device controller, data conversion and more
# (c) 2023, rosandi
#

requirements='''
rich
pillow
requests
numpy
matplotlib
scipy
mseedlib
'''

import sys
import subprocess
from os import path,mkdir,remove
from time import time,sleep
import json

try:
    import requests as rq
    import numpy as np
    from scipy.fftpack import fft
    from scipy.signal import butter,filtfilt,resample
    import wave
    import matplotlib.pyplot as plt
    from mseedlib import MSTraceList, timestr2nstime, sampletime
    from rich.json import JSON
    from rich.console import Console
    from rich.markdown import Markdown
    from PIL import Image

except Exception as e:
    print(e)

    #### Install package if import fails ####
    print('installing package requirements...')
    with open('reqs.txt','w') as reqf: reqf.write(requirements)
    process = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'reqs.txt'], 
            capture_output=True, 
            text=True)
    if process.returncode != 0:
        print('Error installing package: ', process.stderr)
    else:
        print('Package installed successfully!')

    remove('reqs.txt')
    exit()


#----> GOOD TO GO -->

console=Console()


class downloader:
    def __init__(_,devurl):

        if not (devurl.find('http://') == 0):
            devurl=f'http://{devurl}'

        _.devurl=devurl
        _.dir='.'
        #---> DEFAULT TYPE: 16 bit (seismophile, ADS1115)
        _.data_type='int16'

    def command(_, cmd):
        res=rq.get(_.devurl+'/'+cmd, timeout=30)
        return res.text

    def list(_):
        res=rq.get(_.devurl+'/list', timeout=30)
        return json.loads(res.text)

    def info(_,dname):
        res=rq.get(_.devurl+'/fetch?info='+dname, timeout=30)
        return json.loads(res.text)
        
    def fetch(_, dname):
        res=rq.get(_.devurl+'/fetch?data='+dname, timeout=None)
        d=np.frombuffer(res.content, dtype=_.data_type)
        d=np.reshape(d, (len(d)//3,3)).transpose()
        return d

    def save(_, dname, toname=''):
        di=_.info(dname)

        if 'dsize' in di:
            ds=di['dsize']
            if ds==2: _.data_type='int16'
            elif ds==4: _.data_type='int32'
            else:
                raise Exception(f'unimplemented atomic data size: {ds} byte')
                

        dd=_.fetch(dname)
        di['channel-00'] = dd[0].tolist()
        di['channel-01'] = dd[1].tolist()
        di['channel-02'] = dd[2].tolist()
        del di['file']

        if toname=='': toname=dname
        filename=f'{toname}.json'

        with open(_.dir+'/'+filename, 'w') as fl:
            json.dump(di,fl)
            print(f'saved: {filename}')

    def saveall(_, retry=0):
        lst=_.list()
        devname=_.devurl.replace('http://','').replace('.local','')

        for d in lst:
            print(f'loading {d} from {devname}')
            nr=0
            while(nr<=retry):
                try:
                    _.save(d)
                    break
                except Exception as e:
                    print(f'try {nr+1}: {e}')
                    sleep(5) # wait a bit
                    nr+=1
            if nr>retry:
                print(f'failed loading {d} from {devname}')
    
    def remove(_, dname):
        print('removing '+d)
        res=rq.get(f'{_.devurl}/rm?file={dname}')
        print(res.text)

    def remove_all(_):
        lst=_.list()

        for d in lst:
            try:
                print('removing '+d, end='')
                res=rq.get(_.devurl+'/rm?file='+d, timeout=30)
                print(res.text)
            except:
                print('failed', end='')
            finally:
                print('')


### CLASS: Data viewer ###
# attributes:
# data['channel-00|channel-01|channel-02']
#
# Processing is performed using self.dview
# self.data keeps the original data
#

class dataview:
    def __init__(_, dataname, fmt='json'):
        _.dataname=dataname

        _.dview=None
        _.fview=None
        _.hv=None
        _.nseg=1
        _.dtype='i'
        
        if not path.exists(dataname):
            raise Exception('(dataview) data not found: '+dataname)
        
        if fmt=='json': # possible to feed to the next type
            with open(dataname) as fl:
                _.data=json.load(fl)

            ####### backward compatibility ############
            # FIXME!                                  
            if not 'channel-00' in _.data:            
                #print('....>>>>OK...')
                _.dtype='f'                           
                chncount=0
                if 'data' in _.data:
                    for i in range(len(_.data['data'])):  
                        chn='channel-%02d'%(i)            
                        _.data[chn]=_.data['data'][i]     
                
                # in case file doesn't contain data...
                elif ('file' in _.data): 
                    dataname=_.data['file']
                    if dataname.startswith('/'): dataname=dataname.replace('/','')
                    if path.exists(dataname):
                        fmt='bin'
                    else:
                        raise Exception('(dataview) data not available'+_.data['file'])

            ###########################################
 
        if fmt=='bin':
            # complete file pack:
            # - header: dataname.json
            # - binary data: dataname.bin

            if(not path.exists(dataname.replace('.bin','.json'))):
                raise Exception('incomplete data pack')
 
            with open(dataname.replace('.bin','.json')) as fl:
                _.data=json.load(fl)
                del _.data['file']  # remove this tag

            with open(dataname, 'rb') as fl:
                dbin=fl.read()

                if 'dsize' in _.data:
                    ds=_.data['dsize']
                    if ds==2: data_type='int16'
                    elif ds==4: data_type='int32'
                    else:
                        raise Exception(f'unimplemented atomic data size: {ds} byte')

                    print(f'data type: {data_type}')

                d=np.frombuffer(dbin, dtype=data_type)
                
                if 'tail' in _.data:
                    dtail=_.data['tail']//_.data['ch']   # tail must be the scale of n-channel    
                    d=np.reshape(d,(len(d)//3,3))
                    d=d[0:-dtail]
                    d=d.transpose()
                else:
                    d=np.reshape(d, (len(d)//3,3)).transpose()

                _.data['channel-00'] = d[0].tolist()
                _.data['channel-01'] = d[1].tolist()
                _.data['channel-02'] = d[2].tolist()
                _.data['length']=len(d[0])


        n=len(_.data['channel-00'])
        _.ts=_.data['tsample']
        
        # in case given in usecs: convert to secs
        # default in seconds

        if _.ts>1e6: _.ts/=1e6

        _.dt=_.ts/n
        _.fmax=1/_.dt  # full range
        _.xtime=np.linspace(0,_.ts,n)
        _.xfreq=np.linspace(0,_.fmax,n)
        _.length=n
        _.seglen=n
        _.restore()

    def save_mseed(_, fname):
        
        '''
        save data to mseed format
        library used: mseedlib
        '''

        def __record_handler(buffer, hdata):
            hdata['sf'].write(buffer)

        mstl=MSTraceList()
        ''' FDSN:<network>_<station>_<location>_<band>_<source>_<subsource> '''
        curtime=int(time());
        mstl.add_data(sourceid='FDSN:SL_PHI_00_C_H_E',
                      data_samples=_.data['channel-00'],
                      sample_type=_.dtype,
                      sample_rate=1.0/_.dt,
                      start_time_seconds=curtime) 
        # FIXME! use conversion time

        mstl.add_data(sourceid='FDSN:SL_PHI_00_C_H_N',
                      data_samples=_.data['channel-01'],
                      sample_type=_.dtype,
                      sample_rate=1.0/_.dt,
                      start_time_seconds=curtime) 
        # FIXME! use conversion time

        mstl.add_data(sourceid='FDSN:SL_PHI_00_C_H_Z',
                      data_samples=_.data['channel-02'],
                      sample_type=_.dtype,
                      sample_rate=1.0/_.dt,
                      start_time_seconds=curtime) 
        # FIXME! use conversion time

        with open(fname, 'wb') as fl:
            mstl.pack(__record_handler, handlerdata={'sf': fl},
                      format_version=2,
                      record_length=512,
                      flush_data=True)
        
    #resample and save to wav audio file
    def save_wav(_, fname, fscale=10, vol=100):
        newlen=int(_.length*44100*_.dt/fscale)
        #print('newlen=',newlen)

        wfiles=[]

        for fseq in ('channel-00', 'channel-01', 'channel-02') :
            wavsig=resample(_.data[fseq], newlen)
            wavsig=wavsig/np.max(np.abs(wavsig))
            if vol>100: vol=100
            wavsig*=320*vol; #volume
            fseq=fseq.replace('channel','')
            
            if fname.endswith('.wav'):
                aname=fname.replace('.wav', f'{fseq}.wav')
            else:
                aname=fname+f'{fseq}.wav'

            with wave.open(aname,'w') as wfl:
                wfl.setnchannels(1)
                wfl.setsampwidth(2)
                wfl.setframerate(44100)
                wfl.writeframes(wavsig.astype(np.int16).tobytes())
                wfiles.append(aname)

        return tuple(wfiles)
    
    # save/convert to other format: json, mseed, wav
    # this function saves the original data in different format

    def save(_, fname, fmt='mseed', opts=''):
        if fmt == 'json':
            with open(fname, 'w') as fl:
                json.dump(_.data, fl)

        elif fmt == 'mseed':
            _.save_mseed(fname)

        elif fmt == 'wav':
            fscale=10
            vol=100

            if opts:
                if opts.find(',') >0:
                    opt=opts.split(',')
                    fscale=int(opt[0])
                    vol=int(opt[1])
                else:
                    fscale=int(opts)

            _.save_wav(fname, fscale, vol)

    def restore(_):

        # restore variables 
        # dview is restored to the original data

        _.dview=None  # data view
        _.fview=None  # frequency view
        _.hv=None
        _.nseg=1
        _.seglen=_.length

        _.dview =(np.array(_.data['channel-00']),
                  np.array(_.data['channel-01']),
                  np.array(_.data['channel-02']))

    def lowpass(_, freq):
        nf=_.fmax/2
        lf=freq/nf
        if (lf<=0 or lf>=1): return
        _.hv=None
        _.fview=None

        buta, butb = butter(4, lf, btype='low', analog=False)
        _.dview = (filtfilt(buta,butb,_.dview[0]),
                 filtfilt(buta,butb,_.dview[1]),
                 filtfilt(buta,butb,_.dview[2]))

    def highpass(_, freq):
        nf=_.fmax/2
        hf=freq/nf
        if (hf<=0 or hf>=1): return

        _.hv=None
        _.fview=None
        buta, butb = butter(4, hf, btype='high', analog=False)
        _.dview = (filtfilt(buta,butb,_.dview[0]),
                   filtfilt(buta,butb,_.dview[1]),
                   filtfilt(buta,butb,_.dview[2]))

    def transform(_): # FFT transformation
        d=_.dview
        _.fview = (fft(d[0]), fft(d[1]), fft(d[2]))

    def segment(_, n): # reshape data into n segments
        seglen=_.length//n
        
        _.dview=(
                    np.reshape(_.dview[0].flatten()[:seglen*n], (n, seglen)),
                    np.reshape(_.dview[1].flatten()[:seglen*n], (n, seglen)),
                    np.reshape(_.dview[2].flatten()[:seglen*n], (n, seglen))
                )

        _.seglen=seglen
        _.nseg=n

    def slice(_, slice_time): # slice_time in seconds

        n=int(np.floor(_.ts/slice_time)) # number of segment

        if n>0:
            _.segment(n)

    def window(_, fun="hamming"):
        n=_.seglen

        if fun=="hamming":
            w=np.hamming(n)

        elif fun=="blackman":
            w=np.blackman(n)

        elif fun=="kaiser":
            w=np.kaiser(n, 8.6)
            
        else:
            return
        
        _.hv=None
        _.fview=None # force to recalculate
        _.dview*=w

    def plot(_, fname=''):
        # Plots signal 
        # FIXME: 3 channels
        # if fname=='' -> plot to file

        d=_.dview
        n=_.nseg*_.seglen
        xt=np.linspace(0,_.dt*n, n)

        fig, axs = plt.subplots(3)
        axs[0].set_title('X')
        axs[0].plot(xt, d[0].flatten())
        axs[1].set_title('Y')
        axs[1].plot(xt, d[1].flatten())
        axs[2].set_title('Z')
        axs[2].plot(xt, d[2].flatten())
    
        if fname=='':
            plt.show()
        else:
            plt.savefig(fname)
            plt.close()

    def freqrange(_, f, frange):
        
        if frange[1]>0:
            for i in range(len(f)):
                if f[i]>=frange[0]: break
            for j in range(len(f)):
                if f[j]>frange[1]: break

            return i,j

        return 0,len(f)

    def pack_signal(_):
        
        ret={
                'tsample': _.ts,
                'segment': _.nseg,
                'x': _.dview[0].tolist(),
                'y': _.dview[1].tolist(),
                'z': _.dview[2].tolist()
            }

        return ret

    def pack_spectrum(_, smooth: float, average: bool = True, fcut: float =-1.0) -> dict:
        #
        # Pack spectrum to dictionary
        # flimit <=0 no limit
        # WARNING! the fcut is adjusted so that length = nearest power-2 of an integer
        #

        if _.fview is None:
            _.transform()

        if _.nseg==1:
            nn=_.length//2
            xx= np.abs(_.fview[0][:nn])
            yy= np.abs(_.fview[1][:nn])
            zz= np.abs(_.fview[2][:nn])
        
        elif average: # take segment average
            nn=_.seglen//2
            xx=np.zeros(nn)
            yy=np.zeros(nn)
            zz=np.zeros(nn)

            for i in range(_.nseg):
                xx+=np.abs(_.fview[0][i][:nn])
                yy+=np.abs(_.fview[1][i][:nn])
                zz+=np.abs(_.fview[2][i][:nn])

            xx/=_.nseg
            yy/=_.nseg
            zz/=_.nseg

        else:
            nn=_.seglen//2
            xx,yy,zz=[],[],[]
            for i in range(_.nseg):
                xx.append(np.abs(_.fview[0][i][:nn]))
                yy.append(np.abs(_.fview[1][i][:nn]))
                zz.append(np.abs(_.fview[2][i][:nn]))
            xx=np.array(xx)
            yy=np.array(yy)
            zz=np.array(zz)
            #print('check', len(xx), len(xx[0]))

        if fcut>0 and fcut < _.fmax/2:
            ns= _.length if _.nseg==1 else _.seglen
            df=_.fmax/ns
            nf=fcut/df
            snf=np.ceil(np.sqrt(nf))
            nf=int(snf*snf)

            if average or _.nseg == 1:
                xx=xx[:nf]
                yy=yy[:nf]
                zz=zz[:nf]
            else:

                xx=xx[:,:nf]
                yy=yy[:,:nf]
                zz=zz[:,:nf]

            fmax=df*nf

        else:
            fmax=_.fmax/2

        ret={
                'fmax': fmax,
                'segment': _.nseg,
                'X': xx.tolist(),
                'Y': yy.tolist(),
                'Z': zz.tolist()
            }

        if (smooth<1 and smooth>0):
            buta,butb = butter(4, smooth, btype='low', analog=False)
            ret['smooth']=['butterworth', 4, smooth]
            ret['sX']=filtfilt(buta,butb,xx).tolist()
            ret['sY']=filtfilt(buta,butb,yy).tolist()
            ret['sZ']=filtfilt(buta,butb,zz).tolist()
        
        return ret

    def pack_hvsr(_, smooth: float, average: bool = True) -> dict:
        if _.fview is None:
            _.transform()

        ff=_.fview
        h=np.abs(np.sqrt(ff[0]*ff[0]+ff[1]*ff[1]))
        v=np.abs(np.sqrt(ff[2]*ff[2]))

        minv=np.min(v)
        v=(v-minv)+1.0

        hv = h/v
        #hv=v
        ret={
                'fmax': _.fmax/2,
                'segment': _.nseg
            }

        if _.nseg==1:
            nn=_.length//2
            ret['hv']=hv[:nn].tolist()
        elif average:
            nn=_.seglen//2
            vv=np.zeros(nn)
            for i in range(_.nseg):
                vv+=hv[i,:nn]

            ret['hv']=(vv/nn).tolist()
        else:
            rev['hv']=hv[:_.seglen//2].tolist()
       
        if (smooth<1 and smooth>0):
            buta,butb = butter(4, smooth, btype='low', analog=False)
            ret['smooth']=['butterworth', 4, smooth]
            ret['shv']=filtfilt(buta,butb,ret['hv']).tolist()

        return ret

    def plotf(_, fname:str='', smooth: float=0, frange=(0,0)) -> None:
        # Plots data spectrum
        # if fname=='' -> plot to file

        p=_.pack_spectrum(smooth)
        xt=np.linspace(0,p['fmax'],len(p['X']))

        lo,hi=_.freqrange(xt, frange)

        fig, axs = plt.subplots(3)
        plt.xlabel('freq (Hz)')

        axs[0].set_title('X')
        axs[1].set_title('Y')
        axs[2].set_title('Z')

        axs[0].plot(xt[lo:hi], p['X'][lo:hi])
        axs[1].plot(xt[lo:hi], p['Y'][lo:hi])
        axs[2].plot(xt[lo:hi], p['Z'][lo:hi])

        if (smooth<1 and smooth>0):
            axs[0].plot(xt[lo:hi], p['sX'][lo:hi])
            axs[1].plot(xt[lo:hi], p['sY'][lo:hi])
            axs[2].plot(xt[lo:hi], p['sZ'][lo:hi])

        if fname=='':
            plt.show()
        else:
            plt.savefig(fname)
            plt.close()

    def plothv(_, smooth=0, both=False, frange=(0,0), fname='') -> None:
        # Plots HVSR curve
        # if fname=='' -> plot to file

        hv=_.pack_hvsr(smooth);

        plt.ylabel('HVSR')
        plt.xlabel('freq (Hz)')
        xt=np.linspace(0,hv['fmax'],len(hv['hv']))
        lo,hi=_.freqrange(xt,frange)

        if (smooth<1 and smooth>0):
            if both: plt.plot(xt[lo:hi],hv['hv'][lo:hi])
            plt.plot(xt[lo:hi], hv['shv'][lo:hi])
        else:
            plt.plot(xt[lo:hi],hv['hv'][lo:hi])

        if fname=='':
            plt.show()
        else:
            plt.savefig(fname)
            plt.close()


#---> help text
usage="""
# Seismophile Program Usage

## Common parameter

### Convention

- *device_name* --> the name of the seismophile device (**MDNS** name). The name can be replaced by the IP number. **MDNS** name may have *.local* postfix.
- *infile* --> data input file, can be *json* or paired *bin* and *json* header file. Example: ``LOG-0.json``, ``LOG-2.bin`` and ``LOG-2.json`` containing the data header.

```
--param='{json fields definition}'
```

## Device control
    
- list logging data in device: ``dev=device_name ls``
- remove data: ``dev=device_name rm``
- download all data from device: ``dev=device_name save``
- download only one data: ``dev=device_name save=DATA_NAME``

Default: dtype=int16

## Data conversion

- convert to mseed: 
```
convert infile
convert infile outfile.mseed
```

- converting binary file (pair: *.bin, *.json)
```
convert infile.bin
convert infile.bin outfile.mseed
```
or from accompanying ``json`` file:
```
convert infile.json
convert infile.json outfile.[json|mseed]
```

When not supplied at the command prompt, ``mseed`` is the default output file type.

- convert to wav:
```
convert infile outfile.wav
``` 

**WAV conversion parameters**
- _fscale_: frequency scalling
- _volume_: audio volume

**Example**
```json
{"fscale":20,"volume":100}
```

## Process data

```
freq infile outfile.json
freq infile outfile.png
```

Output file depends on the file extension (json or png)

**Parameters:**
            
- _segment_: number of segment (int)
- _slice_: create segments according to time slices (float) 
- _average_: do average (bool)
- _smooth_: smoothing level
- _lof_: high pass frequency
- _hif_: low pass frequency
- _fcut_: high frequency limit
- _imsize_: produced image size (only when converting to image)

**Example**

```json
{"segment":10,"average":true,"smooth":0.1,"hipass":1.0,"lopass":20}
```

## Data inspection

```
show infile.json
show infile.json field
```

# **2022-2025, rosandi**, Geophysics Universitas Padjadjaran

"""

#####################################
# Show the structure of a data file #
def show(fname, fld=''): ############
    try:
        with open(fname) as fl: d=json.load(fl)
        if fld =='':
            rep={}
            for i in d:
                if type(d[i]) == list:
                    rep[i]=f"{type(d[i]).__name__} {np.shape(d[i])}"
                else: 
                    rep[i]=f"{type(d[i]).__name__} {d[i]}"
            
            console.print(JSON(json.dumps(rep)))

        else:
            console.print(f'[blue]{fld}: [green]{d[fld]}')

    except:
        console.print('[red]invalid data file')

###########################################################
#  Create spectrum image                                  #
def to_image(imgname, x, y, z, size=None, lim=8) -> None:##
    # z is vertical
    res=int(np.ceil(np.sqrt(len(x))))

    if res<lim: 
        console.print(f'[red]data number to small: {res}x{res} --> skipping {imgname}')
        return

    if len(x) < res*res:
        tail=np.zeros(res*res-len(x))
        x=np.append(x,tail)
        y=np.append(y,tail)
        z=np.append(z,tail)

    pixel=[]
    row=[]

    for pix in zip(x,y,z):
        row.append(list(pix))
        if len(row) == res:
            pixel.append(row)
            row=[]

    console.print(f'[green]image base resolution: [magenta]{res}x{res}')
    pixel=np.array(pixel)
    img=pixel/np.max(pixel)*255
    #img[0][0]=[255,0,0] # check coord
    img=np.array(img, dtype=np.uint8)
    img=Image.fromarray(img)
    if size:
        if type(size) is int: size=(size,size)
        img=img.resize(size)
    else:
        size=(res,res)

    img.save(imgname)
    console.print(f'[magenta]{imgname} [green]created image size: [magenta]{size[0]}x{size[1]}')


##################
# MAIN FUNCTION  #
def main_func():##
    import sys
    dev=None
    dvi=None
    ntry=5
    opts=''
    pars={}

    ai=0
    while ai < len(sys.argv):

        arg=sys.argv[ai]

        if len(sys.argv)==1 or arg=="help" or arg=="--help": 
            console.print(Markdown(usage))
            exit()

        if arg.startswith("--param="): 
            # multipurpose parameters in json format
            # this must come first

            try:
                jsontext=arg.replace('--param=','')
                pars=json.loads(jsontext)
                console.print('[green]Common parameters:')
                console.print(JSON(jsontext))

            except Exception as e:
                console.print(f'wrong parameter {arg}')
                console.print(e)

        # when accessing a device, this must be among the first arguments
        if arg.find('dev=') == 0:
            dev=downloader(arg.replace('dev=', ''))

        if arg.find('ls') == 0:
            if dev: 
                lst=dev.list()
                for i in lst:
                    print(f'{i}: {lst[i]}')

        if arg.find('fetch=') == 0:
            if dev: dev.save(arg.replace('fetch=',''))

        if arg.find('save') == 0:
            logfile=None
            if arg.find('save=')==0:
                logfile=arg.replace('save=','')

            try:
                
                if dev: 
                    dev.dir=dev.devurl.replace('http://','').replace('.local','')
                    if not path.exists(dev.dir):
                        mkdir(dev.dir)
                    
                    if logfile:
                        dev.save(logfile)
                    else:
                        dev.saveall(ntry)

            except Exception as e:
                raise e

        if arg.find('ntry=') == 0:
            ntry=int(arg.replace('ntry=',''))

        if arg.find('rm') == 0:
            if dev: dev.remove_all()
        
        ##################################
        # Data CONVERSION functions      #
        if arg.startswith('convert'):#####
            fmt=''
            try: 
                dfile=sys.argv[ai+1]
                if dfile.endswith('.bin'): fmt='bin'
                if dfile.endswith('.json'): fmt='json'
            except:
                console.print('[red][bold]input filename required!')
                exit()
            
            try: 
                ofile=sys.argv[ai+2]
                ai+=2
            except:
                if dfile.endswith('.bin'): 
                    ofile=dfile.replace('.bin','.mseed')
                elif dfile.endswith('.json'): 
                    ofile=dfile.replace('.json','.mseed')

            if ofile.endswith('.mseed'):
                dataview(dfile,fmt).save_mseed(ofile)
                console.print(f'[green]file {ofile} saved')

            elif ofile.endswith('.wav'): 
                dvi=dataview(dfile,fmt)
                wfiles=dvi.save_wav(ofile,
                             10 if not 'fscale' in pars else pars['fscale'],
                             100 if not 'volume' in pars else pars['volume'])

                console.print(f'created: {wfiles}')

            else: # consider json output
                if not ofile.endswith('.json'): ofile=ofile+'.json'
                dataview(dfile,fmt).save(ofile,'json')
        
        ################################
        # calculate frequency spectrum #
        if arg.startswith('freq'):######
                            
            try:
                dfile=sys.argv[ai+1]
                ofile=sys.argv[ai+2]
                ai+=2
            except:
                console.print(f'[red][bold]input and output filename required')
                exit()

            dv=dataview(dfile)
            if 'segment' in pars: dv.segment(pars['segment'])
            elif   'slice' in pars: dv.slice(pars['slice'])
            if 'hif' in pars: dv.lowpass(pars['hif'])
            if 'lof' in pars: dv.highpass(pars['lof'])
            if 'window' in pars: dv.window(pars['window'])

            fspec=dv.pack_spectrum(
                    0 if not 'smooth' in pars else pars['smooth'], 
                    True if not 'average' in pars else pars['average'],
                    -1 if not 'fcut' in pars else pars['fcut'])

            #-----> Create IMAGE
            if ofile.endswith('.png') or ofile.endswith('.jpg'):
                
                if 'smooth' in pars:
                    R,G,B = fspec['sX'], fspec['sY'], fspec['sZ']
                else:
                    R,G,B = fspec['X'], fspec['Y'], fspec['Z']

                if dv.nseg==1:
                    to_image(ofile, R, G, B,
                             None if not 'imsize' in pars else pars['imsize'])
                
                else:
                    ave=True if not 'average' in pars else pars['average']

                    if ave:
                        to_image(ofile, R, G, B, 
                                 None if not 'imsize' in pars else pars['imsize'])

                    else:
                        for i in range(len(R)):
                            ext='.jpg' if ofile.endswith('.jpg') else '.png'
                            fnm=ofile.replace(ext,'-%03d'%(i)+ext)

                            to_image(fnm, R[i], G[i], B[i],
                                     None if not 'imsize' in pars else pars['imsize'])

            #-----> Write data in JSON
            elif ofile.endswith('.json'):
                with open(ofile,'w') as ofl: json.dump(fspec,ofl)

        #################################
        # Show what is in the data file #
        if arg.startswith('show'): ######
            try:
                fnm=sys.argv[ai+1]
                field='' if len(sys.argv) == ai+2 else sys.argv[ai+2]
                show(fnm, field)

            except:
                console.print('[red]nothing to show')

            finally:
                exit()

        ai+=1 # next param


############################
# MAIN PROGRAM             #
if __name__ == '__main__':##

    try:
        main_func()

    except Exception as e:
        print('****Error occurred****')
        print(e)

#main_func()