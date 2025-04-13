import struct
import os

POINTER_FORMAT= 'i'
POINTER_SIZE=struct.calcsize(POINTER_FORMAT)

class Venta:

    FORMAT = 'i30sif10si'+2*POINTER_FORMAT  
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, id, nombre, cantidad, precio, fechaVenta, balanceFactor=0, left=-1,right=-1):
        self.id = id
        self.nombre = nombre[:30].ljust(30)
        self.cantidad = cantidad
        self.precio = precio
        self.fechaVenta = fechaVenta[:10].ljust(10)
        self.balanceFactor=balanceFactor
        self.left = left
        self.right=right

    def __str__(self):
        return f"id: {self.id} Nombre: {self.nombre} Cantidad: {self.cantidad} FechaVenta: {self.fechaVenta} Balance Factor: {self.balanceFactor} left: {self.left} right: {self.right}"
    
    def getIndexChild(self,choose):
        return self.left if choose==-1 else self.right
    
    def setIndexChild(self,choose,value):
        if choose==-1:
            self.left=value
        else:
            self.right=value
        
class BaseFile:
    COUNT_REGISTER_FORMAT = 'i'
    HEADER_FORMAT = POINTER_FORMAT+COUNT_REGISTER_FORMAT


    COUNT_REGISTER_SIZE=struct.calcsize(COUNT_REGISTER_FORMAT)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, filename, ruta=None):
        self.filename = filename
        self.createFile(ruta)

    def createFile(self,ruta):
        with open(self.filename, "wb") as file:
            file.write(struct.pack(POINTER_FORMAT,-1))
            file.write(struct.pack(BaseFile.COUNT_REGISTER_FORMAT,0))
            
        if ruta!=None:
            with open(ruta, "r") as archivo:
                next(archivo)
                for linea in archivo:
                    id,nombre,cantidad,precio,fechaVenta= tuple(linea.strip().split(","))  # Elimina saltos de línea y separa por comas
                    venta=Venta(int(id),nombre,int(cantidad),float(precio),fechaVenta)
                    self.insert(venta)
            
    def packRecord(self, record):
        return struct.pack(Venta.FORMAT,
            record.id,
            record.nombre.encode('latin-1'),
            record.cantidad,
            record.precio,
            record.fechaVenta.encode(),
            record.balanceFactor,
            record.left,
            record.right
        )

    def unpackRecord(self, data):
        id, nombre, cantidad, precio, fechaVenta,balanceFactor, left,right= struct.unpack(Venta.FORMAT, data)
        return Venta(
            id,
            nombre.decode('latin-1').strip(),
            cantidad,
            precio,
            fechaVenta.decode().strip(),
            balanceFactor,
            left,
            right,
        )
    
    def getAllRecords(self):
        # Devuelve todos los registros válidos.
        records = []
        with open(self.filename, "rb") as file:
            index = 0
            while True:
                file.seek(BaseFile.HEADER_SIZE+index*Venta.SIZE)
                data = file.read(Venta.SIZE)
                if not data:
                    break
                index += 1

                record = self.unpackRecord(data)
                records.append(record)
        return records
    
    def getRecord(self,index):
        if index==-1:
            return None

        self.file.seek(BaseFile.HEADER_SIZE+index*Venta.SIZE)
        record=self.unpackRecord(self.file.read(Venta.SIZE))
        record.index=index
        return record
        
    def setRecord(self,record):
        self.file.seek(BaseFile.HEADER_SIZE+record.index*Venta.SIZE)
        self.file.write(self.packRecord(record))
        
    def appendRecord(self,record):
        self.file.seek(0,os.SEEK_END)
        self.file.write(self.packRecord(record))
        record.index=self.getCountRegister()
        self.incrementCountRegister()
        return record
    
    def getIndexHead(self):
        with open(self.filename, "rb+") as file:
            file.seek(0)
            return struct.unpack(POINTER_FORMAT,file.read(POINTER_SIZE))[0]
            
    def setIndexHead(self,value):
        self.file.seek(0)
        self.file.write(struct.pack(POINTER_FORMAT,value))
        
    def getCountRegister(self):
        self.file.seek(POINTER_SIZE)
        return struct.unpack(BaseFile.COUNT_REGISTER_FORMAT,self.file.read(BaseFile.COUNT_REGISTER_SIZE))[0]

    def incrementCountRegister(self):
        count=self.getCountRegister()
        self.file.seek(POINTER_SIZE)
        self.file.write(struct.pack(BaseFile.COUNT_REGISTER_FORMAT,count+1))

    def decrementCountRegister(self):
        count=self.getCountRegister()
        self.file.seek(POINTER_SIZE)
        self.file.write(struct.pack(BaseFile.COUNT_REGISTER_FORMAT,count-1))

# En todos se evito metodos recursivos, con metodos iterativos disminuimos la sobrecarga en el stack en la memoria principal 

class AvlFile(BaseFile):

    def insert(self, record):
        with open(self.filename, "rb+") as file:
            self.file=file
            if (self.getIndexHead()==-1):
                self.appendRecord(record)
                self.setIndexHead(0)
            else:
                T=None # Siempre apunta al padre de S
                S=self.getRecord(self.getIndexHead()) # S apuntara posible nodo que necesite balanceo
                P=S # P sera el puntero que se desaplazara hacia abajo
                
                # Etapa 1: Busqueda de posicion a insertar nodo
                while True:
                    if (record.id<P.id):
                        Q=self.getRecord(P.left)
                        childSide=-1
                    elif (record.id>P.id):
                        Q=self.getRecord(P.right)
                        childSide=1
                    else:
                        print(f"Error: Ya existe un registro con ID : {record.id}")
                        return
                    
                    if (Q==None): break   
                    if(Q.balanceFactor!=0): T=P;S=Q
                    P=Q  

                # Etapa 2: Insercion de nodo

                Q=self.appendRecord(record)
                P.setIndexChild(childSide,Q.index)
                self.setRecord(P)

                # Etapa 3: Ajuste de factores de balanceo
                if (record.id<S.id):
                    childSide=-1
                else:
                    childSide=1
                
                P=self.getRecord(S.getIndexChild(childSide))
                R=P

                while (P.id!=Q.id):
                    if (record.id<P.id):
                        childSide2=-1
                    elif (record.id>P.id):
                        childSide2=1
                    P.balanceFactor=childSide2
                    self.setRecord(P)
                    P=self.getRecord(P.getIndexChild(childSide2))
                

                # Etapa 4: Rebalanceo de arbol

                if (S.balanceFactor==0): # El arbol crecio pero no se desbalanceo
                    S.balanceFactor=childSide
                    self.setRecord(S)
                elif (S.balanceFactor==-childSide):  # El arbol se balanceo mas
                    S.balanceFactor=0
                    self.setRecord(S)
                elif (S.balanceFactor==childSide):  # El arbol esta desbalanceado
                    if(R.balanceFactor==childSide):  # Se requiere de rotacion simple
                        P=R
                        S.setIndexChild(childSide,R.getIndexChild(-childSide))
                        R.setIndexChild(-childSide,S.index)
                        S.balanceFactor=0
                        R.balanceFactor=0
                        self.setRecord(S)
                        self.setRecord(R)

                    elif (R.balanceFactor==-childSide):  # Se requiere de rotacion doble
                        P=self.getRecord(R.getIndexChild(-childSide))
                        R.setIndexChild(-childSide,P.getIndexChild(childSide))
                        P.setIndexChild(childSide,R.index)
                        S.setIndexChild(childSide,P.getIndexChild(-childSide))
                        P.setIndexChild(-childSide,S.index)

                        if (P.balanceFactor==childSide):
                            S.balanceFactor=-childSide
                            R.balanceFactor=0
                        elif (P.balanceFactor==0):
                            S.balanceFactor=0
                            R.balanceFactor=0
                        elif (P.balanceFactor==-childSide):
                            S.balanceFactor=0
                            R.balanceFactor=childSide
                        
                        P.balanceFactor=0
                        self.setRecord(P)
                        self.setRecord(R)
                        self.setRecord(S)

                    # Etapa 5: Actualizacion de pointer a nodo padre
                    if (T==None):
                        if (S.index==self.getIndexHead()):
                            self.setIndexHead(P.index)
                    else:
                        if (S.id==self.getRecord(T.right).id):
                            T.right=P.index
                        else:
                            T.left=P.index
                        self.setRecord(T) 
    
    
    def remove(self, key):
        with open(self.filename, "rb+") as file:
            self.file=file
            if (self.getIndexHead()==-1):
                print(f"Error: El archivo no tiene registros")
            else:
                T=None # Siempre apunta al padre de S
                S=self.getRecord(self.getIndexHead()) # S apuntara posible nodo que necesite balanceo

                O=None
                P=S # P sera el puntero que se desaplazara hacia abajo
                
                # Etapa 1: Busqueda de posicion a insertar nodo
                while True:
                    if (key<P.id):
                        Q=self.getRecord(P.left)
                        childSide=-1
                    elif (key>P.id):
                        Q=self.getRecord(P.right)
                        childSide=1
                    else:
                        break
                    
                    if (Q==None): print(f"Error: No existe un registro con ID : {key}"); return

                    if(Q.balanceFactor!=0): T=P;S=Q
                    O=P
                    P=Q  

                # Etapa 2: Eliminacion de nodo

                if (P.left==-1 and P.right==-1):
                    O.setIndexChild(childSide,-1)
                elif (P.left!=-1 and P.right==-1):
                    P=self.getRecord(P.left)
                    O.setIndexChild(childSide,P.index)
                else:
                    Pini=P
                    O2=P
                    P=self.getRecord(P.right)
                    childSide2=1

                    while(P.left!=-1):
                        O2=P
                        P=self.getRecord(P.left)
                        childSide2=-1

                    O2.setIndexChild(childSide2,P.right)
                    P.left=Pini.left
                    P.right=Pini.right

                    if O==None:
                        self.setIndexHead(P.index)
                    else: 
                        O.setIndexChild(childSide,P.index)

                    self.setRecord(O2)
                    self.setRecord(P)
                    
                if O!=None: self.setRecord(O)
              
    def search(self, key):
        with open(self.filename, "rb+") as file:
            self.file=file
            P=self.getRecord(self.getIndexHead()) # P sera el puntero que se desaplazara hacia abajo
            while True:
                if (key<P.id):
                    Q=self.getRecord(P.left)
                elif (key>P.id):
                    Q=self.getRecord(P.right)
                else:
                    return P
                if (Q==None): 
                    print(f"Error: No existe un registro con ID : {key}")
                    break
                P=Q 
    
    def rangeSearch(self, init_key, end_key):
        with open(self.filename, "rb+") as file:
            self.file=file
            records=[]
            stackIndex = []
            record = self.getRecord(self.getIndexHead())

            while stackIndex or record:
                while record:
                    stackIndex.append(record.index)
                    if record.id > init_key:
                        record = self.getRecord(record.left)
                    else:  # Si init_key es mayor entonces se descarta todo el subarbol izquierdo
                        break  

                record = self.getRecord(stackIndex.pop())

                if init_key <= record.id <= end_key:
                    records.append(record)

                if record.id < end_key:
                    record = self.getRecord(record.right)
                else:  # Si end_key es mayor entonces se descarta todo el subarbol derecho, y terminamos ya que estamos inorder
                    record = None

            return records



avlFile = AvlFile("ventas.dat","sales_dataset_prueba.csv")

ventas=avlFile.getAllRecords()
print("Operacion Insert:\nHeader Pointer: ",avlFile.getIndexHead())
for venta in ventas:
    print(venta)

print()

avlFile.remove(4)
print("Operacion Remove: \nHeader Pointer: ",avlFile.getIndexHead())
ventas=avlFile.getAllRecords()
for venta in ventas:
    print(venta)
print()

print("Operacion search for key:")
venta=avlFile.search(20)
print(venta)
print()

print("Operacion search in range:")
ventas=avlFile.rangeSearch(8,20)
for venta in ventas:
    print(venta)