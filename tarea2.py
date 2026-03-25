import random
import threading
from threading import Thread, Semaphore
import time

# CONSTANTES
NECESITA_AYUDA = 3 #Num elfos necesarios para despertar a Santa
MAX_ELFOS = 10 #Num elfos totales
NUM_RENOS = 9 #Num renos totales

#Contadores
contador_elfos = 0 #Permite contar cuantos elfos necesitan ayuda
contador_renos = 0 #Permite contar cuantos renos vuelven de vacaciones

#Semáforos
santaSem = threading.Semaphore(0) #Sirve para controlar el hilo de santa. 
renoSem = threading.Semaphore(0) #Sirve para controlar el hilo de santa.

#Mutex implementados con semáforos
mutex_num_elfos = threading.Semaphore(3) #
mutex = threading.Semaphore(1) #Permite el control del acceso a las variables contador


#Listas de hilos: Creo que no son necesarios
hilos_elfos = []
hilos_renos = []

#Define el comportamiento de Santa Claus
def santa():
    global contador_elfos, contador_renos

    while True:
        print(f'Santa está durmiendo ZZZ')

        santaSem.acquire()
        mutex.acquire()

        print(f'Despertaron a Santa')

        if contador_renos == 9:

            #Reinicia el contador de renos
            contador_renos = 0

            print(f'Santa va a repartir regalos')
            [renoSem.release() for _ in range(NUM_RENOS)] #Manda a los renos de "vacaciones"

        elif contador_elfos == 3:

            #Reinicia el contador de los elfos
            contador_elfos = 0

            print('Santa está ayudando a los elfos')
            time.sleep(random.uniform(0,0.3)) #Simula que tardó unos instantes en ayudar a los elfos
            print('Santa terminó de ayudar a los elfos')
            [mutex_num_elfos.release() for _ in range(NECESITA_AYUDA)]


        mutex.release()


#Define el comportamiento de los renos
def renos(n):
    global contador_renos

    while True:
        time.sleep(random.uniform(1,3)) ##Simulan la aleatoriedad del tiempo de vacaciones de los renos

        mutex.acquire()

        contador_renos += 1
        print(f'El reno {n} regresó de sus vacaciones. Van {contador_renos}/9')
        if contador_renos == 9:
            santaSem.release()

        mutex.release()
        renoSem.acquire()


#Define el comportamiento de los elfos
def elfos(n):
    global contador_elfos
    
    while True:
        #elfos trabajan
        time.sleep(random.uniform(1,2)) ##Simulan la aleatoriedad de las dudas del los elfos

        mutex_num_elfos.acquire() #Permite el control de los 3 elfos
        mutex.acquire() #Impide condiciones de carrera al ingresar a la variable contador_elfos

        contador_elfos += 1
        print(f'Elfo {n} necesita ayuda. Van {contador_elfos}/3')

        if contador_elfos == 3:
            santaSem.release() #Despiertan a Santa

        mutex.release()


##Permite crear los hilos a utilizar en el programa
def inicializar_hilos():
    Thread(target=santa).start()

    for i in range (NUM_RENOS):
        hilos_renos.append(Thread(target=renos, args=[i]).start())

    for i in range (MAX_ELFOS):
        hilos_elfos.append(Thread(target=elfos, args=[i]).start())

def main():
    inicializar_hilos()


if __name__ == "__main__":
    main()