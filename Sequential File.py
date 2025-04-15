import os
import struct
import csv

# Formato del registro: int, 30s, int, float, 10s, int (activo o eliminado)
RECORD_FORMAT = "i30sif10si"
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)

class Venta:
    def __init__(self, id, nombre, cantidad, precio, fechaVenta, activo=1):
        self.id = id
        self.nombre = nombre[:30].ljust(30)
        self.cantidad = cantidad
        self.precio = precio
        self.fechaVenta = fechaVenta[:10].ljust(10)
        self.activo = activo

    def to_bytes(self):
        return struct.pack(RECORD_FORMAT, self.id, self.nombre.encode('latin1'), self.cantidad, self.precio, self.fechaVenta.encode('latin1'), self.activo)

    @staticmethod
    def from_bytes(data):
        id, nombre, cantidad, precio, fechaVenta, activo = struct.unpack(RECORD_FORMAT, data)
        return Venta(id, nombre.decode('latin1').strip(), cantidad, precio, fechaVenta.decode('latin1').strip(), activo)

class SequentialFile:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            open(self.filename, 'wb').close()

    def insert(self, record: Venta):
        with open(self.filename, 'ab') as f:
            f.write(record.to_bytes())

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

