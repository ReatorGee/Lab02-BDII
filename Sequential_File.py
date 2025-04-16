import os
import struct
import csv

# Formato del registro: int, 30s, int, float, 10s, int (activo o eliminado)
FORMAT = "<i30sif10si1si"
RECORD_SIZE = struct.calcsize(FORMAT)

class Venta:
    def __init__(self, id, nombre, cantidad, precio, fechaVenta, indice='-1', filetype='d', activo=1):
        self.id = id
        self.nombre = nombre[:30].ljust(30)
        self.cantidad = cantidad
        self.precio = precio
        self.fechaVenta = fechaVenta[:10].ljust(10)
        self.indice = indice
        self.filetype = filetype
        self.activo = activo

    def to_bytes(self):
        return struct.pack(FORMAT, self.id, self.nombre.encode('latin1'), self.cantidad, self.precio, self.fechaVenta.encode('latin1'), self.indice, self.filetype.encode('latin1'), self.activo)

    @staticmethod
    def from_bytes(data):
        id, nombre, cantidad, precio, fechaVenta, indice, filetype, activo = struct.unpack(FORMAT, data)
        return Venta(id, nombre.decode('latin1').strip(), cantidad, precio, fechaVenta.decode('latin1').strip(), indice, filetype.encode('latin1'), activo)

class SequentialFile:

    def __init__(self, filename, auxfile, k):
        self.filename = filename
        self.auxfile = auxfile
        self.k = k
        if not os.path.exists(self.filename):
            open(self.filename, 'wb').close()
        if not os.path.exists(self.auxfile):
            open(self.auxfile, 'wb').close()

    def insert(self, record: Venta):
        limit = self.k
        with open(self.filename, 'r+b') as file:
            
            while True:
                default_index = 0

                index_data = file.read(4)
                binary_data = file.read(RECORD_SIZE)
                if not index_data:
                    file.write(struct.pack('i', default_index))
                    file.write(Venta.to_bytes(record))
                    break
                temp = Venta.from_bytes(binary_data)
                index = struct.unpack('i', index_data)[0]

                next_index_data = file.read(4)
                next_data = file.read(RECORD_SIZE)
                if not next_index_data:
                    if temp.activo == 0:
                        file.seek(index * (RECORD_SIZE + 4))
                        file.write(Venta.to_bytes(record))
                    else:
                        file.write(struct.pack('i', index + 1))
                        file.write(Venta.to_bytes(record))
                else:
                    index2 = struct.unpack('i', next_index_data)[0]
                    temp2 = Venta.from_bytes(next_data)

                    #overflow
                    if temp.id < record.id < temp2.id:
                        with open(self.auxfile, 'ab') as aux:
                            aux_index = 0
                            registers = []

                            if limit == 0:

                                file.seek(0)
                                while True:
                                    check = file.read(4)
                                    if not check:
                                        break
                                    register_data = file.read(RECORD_SIZE)
                                    register = Venta.from_bytes(register_data)
                                    registers.append(register)

                                while True:
                                    check2 = aux.read(4)
                                    if not check2:
                                        break
                                    register_data_aux = aux.read(RECORD_SIZE)
                                    register_aux = Venta.from_bytes(register_data_aux)
                                    registers.append(register_aux)

                                registers.append(Venta.record)

                                registers.sort(key=lambda r: r.id)
                                with open("nuevo_principal.dat", "wb") as f_principal:
                                    for reg in registers:
                                        f_principal.write(reg.to_bytes())
                            else:
                                while True:
                                    aux_data = file.read(RECORD_SIZE + 4)
                                    if not aux_data:
                                        aux.write(struct.pack('i', aux_index))

                                        record.indice = index2
                                        temp.indice = aux_index
                                        temp.filetype = 'a'

                                        aux.write(Venta.to_bytes(record))
                                        limit -= 1

                                        file.seek(index * (RECORD_SIZE + 4))
                                        file.write(Venta.to_bytes(temp))
                                        break
                                    

    def search(self, id):
        with open(self.filename, 'rb') as f:
            while True:
                data = f.read(RECORD_SIZE)
                if not data:
                    break
                if len(data) < RECORD_SIZE:
                    break
                record = Venta.from_bytes(data)
                if record.id == id and record.activo:
                    return record
        return None

    def delete(self, id):
        found = False
        with open(self.filename, 'r+b') as f:
            pos = 0
            while True:
                data = f.read(RECORD_SIZE)
                if not data:
                    break
                if len(data) < RECORD_SIZE:
                    break
                record = Venta.from_bytes(data)
                if record.id == id and record.activo:
                    record.activo = 0
                    f.seek(pos)
                    f.write(record.to_bytes())
                    found = True
                    break
                pos += RECORD_SIZE
        return found

    def range_search(self, lower, upper):
        results = []
        with open(self.filename, 'rb') as f:
            while True:
                data = f.read(RECORD_SIZE)
                if len(data) < RECORD_SIZE:
                    break
                record = Venta.from_bytes(data)
                if record.activo and lower <= record.id <= upper:
                    results.append(record)
        return results


def cargar_csv(archivo_csv, archivo_bin):
    sf = SequentialFile(archivo_bin)
    with open(archivo_csv, newline='', encoding='latin1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            venta = Venta(
    int(row['ID de la venta']),
    row['Nombre producto'],
    int(row['Cantidad vendida']),
    float(row['Precio unitario']),
    row['Fecha de venta']
)
            sf.insert(venta)

if os.path.exists("ventas.dat"):
    os.remove("ventas.dat")

cargar_csv("sales_dataset.csv", "ventas.dat")

# Verificamos si se insertaron correctamente
sf = SequentialFile("ventas.dat")
for record in sf.range_search(100, 105):
    print(f"{record.id} - {record.nombre} - {record.cantidad} - {record.precio} - {record.fechaVenta}")


sf = SequentialFile("ventas.dat")
sf.insert(Venta(101, "Galletas", 10, 2.5, "2025-04-14"))
sf.insert(Venta(102, "Agua", 20, 1.2, "2025-04-15"))

# Buscar un registro
r = sf.search(101)
if r:
    print(f"{r.nombre} - {r.precio}")

# Eliminar un registro
sf.delete(101)

# Buscar por rango
for r in sf.range_search(1, 100):
    print(f"{r.id:<3} | {r.nombre.strip():<30} | {r.cantidad:<3} | {r.precio:<8} | {r.fechaVenta.strip()}")

