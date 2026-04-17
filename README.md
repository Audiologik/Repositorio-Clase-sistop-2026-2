Tarea 3 - MéridaFrancisco - QuezadaLeonardo
# Tarea Planificadores de procesos.

Para esta tarea implementamos los planificadores de procesos FCFS, RR1 (con quantum =1 ), RR4 (quantum = 4) y SPN, además de agregar el esquema visual para mejorar su presentación y comprobar su funcionamiento.

## Entorno de desarrollo
Realizamos lo solicitado en un programa desarrollado en python versión 3.12.3, llamado “T03.py” por lo que puede ser ejecutado en cualquier sistema operativo que cuente con Python3.
Forma de ejecutarlo

### Ejecución:

Para ejecutar, realizar la siguiente instrucción: :> python3 T03.py

### Implementación:

Para nuestra implementación empleamos un objeto llamado “Proceso” el cual simulará la llegada de un nuevo proceso a una lista de procesos pendientes. Este objeto tiene como atributos un id, el tiempo en el que llegó a la fila, el tiempo que necesita para ejecutarse y un atributo “falta” que permite implementar el planificador RR. Estos valores fueron generados aleatoriamente.

Los procesos son almacenados y ordenados según el tiempo de llegada, en una lista para poder trabajar con los planificadores.

# Planificadores
Como mencionamos antes, estos planificadores reciben una lista ordenada de procesos.

## FCFS
Al recibir una lista ordenada de los procesos simulados, para mostrar el orden de ejecución de dichos procesos, únicamente recorremos la lista recibida e imprimimos sus identificadores tantas veces dure el proceso.  

Para el cálculo de las métricas de desempeño, llevamos un control del tiempo (inicio y fin de ejecución) con una variable contador llamada “tiempo”. Por último, regresamos el orden de ejecución y las métricas promedio por cada lista de procesos.

## RR (Round Robin)

Para nuestra implementación, simulamos el paso del tiempo con una variable contador “tiempo” la cual empieza en el momento 0. Implementamos el uso de una cola para llevar el control de los procesos.

Primeramente, iniciamos un ciclo “while” que iterará mientras haya procesos formados en la cola o falten procesos por llegar en el momento en el que se analiza.

Mediante otro while formamos en la cola a todos los procesos que tiene un tiempo de llegada igual o menor al tiempo analizado.

Si la cola no está vacía, mientras que el tiempo en el que se está ejecutando no supere el tiempo del quantium o no se haya finalizado el proceso, guardamos el id del proceso en ejecución, disminuimos “falta” (tiempo restante de ejecución) e incrementamos la variable “tiempo”.

Cada vez que incrementamos el tiempo, revisamos si hay nuevos procesos que inician en el tiempo actual, de ser así, los formamos en la cola.

Por último, si terminamos la ejecución de un proceso “proceso.falta = 0”, calculamos sus métricas de desempeño y las almacenamos para calcular el promedio total.

Para variar entre RR1 y RR4, únicamente hace falta variar el valor de la variable “quantium”.

## SPN

Para la implementación se requirieron de variables que muestren el estado de los procesos a lo largo de su ejecución, por ejemplo la variable “completados” nos permite tener un control de los procesos que ya han terminado para saber si terminar de ejecutar el algoritmo. 

Comenzamos creando una copia de los procesos, ya que iteramos y modificamos sobre estos.

Mediante un ciclo “while” que itera mientras haya procesos no terminados se determina un arreglo de procesos disponibles, en el que se buscará al proceso más corto mediante una función lambda la cual, de todos los procesos disponibles toma el que tiene un menor tiempo “t”.

Posteriormente se toma el tiempo de ejecución “t” para “ejecutar” el proceso (Añade su nombre a la variable “orden procesos”) sumando el paso del tiempo.

Finalmente cuando el proceso ha sido completado se miden sus métricas de desempeño, para luego añadir ese proceso a la variable “completados” y al arreglo de terminados

Al terminar con todos los procesos se hace un promedio de todas las métricas.
