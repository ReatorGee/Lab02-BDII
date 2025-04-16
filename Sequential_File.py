import struct
import os

# Definición del formato: < indica little-endian y sin padding
FORMAT = "<i30sif10si1si"
RECORD_SIZE = struct.calcsize(FORMAT)

class Venta:
    def __init__(self, id, nombre, cantidad, precio, fechaVenta, indice=-1, filetype='d', activo=1):
        self.id = id
        self.nombre = nombre[:30].ljust(30)
        self.cantidad = cantidad
        self.precio = precio
        self.fechaVenta = fechaVenta[:10].ljust(10)
        self.indice = indice
        self.filetype = filetype
        self.activo = activo

    def to_bytes(self):
        return struct.pack(
            FORMAT,
            self.id,
            self.nombre.encode('latin1'),
            self.cantidad,
            self.precio,
            self.fechaVenta.encode('latin1'),
            int(self.indice),
            self.filetype.encode('latin1'),
            self.activo
        )

    @staticmethod
    def from_bytes(data):
        id, nombre, cantidad, precio, fechaVenta, indice, filetype, activo = struct.unpack(FORMAT, data)
        return Venta(
            id,
            nombre.decode('latin1').strip(),
            cantidad,
            precio,
            fechaVenta.decode('latin1').strip(),
            indice,
            filetype.decode('latin1').strip(),
            activo
        )

class SequentialFile:
    def __init__(self, filename, auxfile, k):
        self.filename = filename
        self.auxfile = auxfile
        self.k = k  # límite del auxiliar
        if not os.path.exists(self.filename):
            open(self.filename, 'wb').close()
        if not os.path.exists(self.auxfile):
            open(self.auxfile, 'wb').close()

    def insert(self, record: Venta):
        inserted = False
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            pos = 0
            while True:
                current_pos = file.tell()
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not index_data or not data:
                    break

                index = struct.unpack('<i', index_data)[0]
                current = Venta.from_bytes(data)

                next_pos = file.tell()
                next_index_data = file.read(4)
                next_data = file.read(RECORD_SIZE)

                if not next_index_data or not next_data:
                    break

                next_index = struct.unpack('<i', next_index_data)[0]
                next_record = Venta.from_bytes(next_data)

                if current.id < record.id < next_record.id:
                    if self.k == 0:
                        self.rebuild()
                        self.insert(record)
                        return
                    else:
                        with open(self.auxfile, 'ab') as aux:
                            aux_index = aux.tell() // (4 + RECORD_SIZE)
                            aux.write(struct.pack('<i', -1))
                            aux.write(record.to_bytes())
                            # Actualizar punteros lógicos
                            current.indice = aux_index
                            current.filetype = 'a'
                            file.seek(current_pos + 4)  # después del índice
                            file.write(current.to_bytes())
                            self.k -= 1
                            inserted = True
                            break

                file.seek(next_pos)

            if not inserted:
                file.seek(0, os.SEEK_END)
                file.write(struct.pack('<i', -1))
                file.write(record.to_bytes())

    def rebuild(self):
        registros = []
        # Leer archivo principal
        with open(self.filename, 'rb') as file:
            while True:
                index_data = file.read(4)
                if not index_data:
                    break
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1:
                    registros.append(reg)

        # Leer archivo auxiliar
        with open(self.auxfile, 'rb') as aux:
            while True:
                index_data = aux.read(4)
                if not index_data:
                    break
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1:
                    registros.append(reg)

        # Ordenar registros
        registros.sort(key=lambda r: r.id)

        # Reescribir archivo principal
        with open(self.filename, 'wb') as file:
            for reg in registros:
                reg.indice = -1
                reg.filetype = 'd'
                file.write(struct.pack('<i', -1))
                file.write(reg.to_bytes())

        # Vaciar auxiliar
        open(self.auxfile, 'wb').close()
        self.k = 10  # reinicia el contador del auxiliar a su valor máximo

                                    

    def search(self, id):
        with open(self.filename, 'rb') as file:
            while True:
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    return reg
                # Si hay un puntero al auxiliar, seguimos buscando
                if reg.indice != -1 and reg.filetype == 'a':
                    found = self._search_aux(id, reg.indice)
                    if found:
                        return found
        return None

    def _search_aux(self, id, start_index):
        with open(self.auxfile, 'rb') as aux:
            current_index = start_index
            while current_index != -1:
                pos = current_index * (4 + RECORD_SIZE)
                aux.seek(pos)
                index_data = aux.read(4)
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    return reg
                current_index = reg.indice if reg.filetype == 'a' else -1
        return None


    def delete(self, id):
        with open(self.filename, 'r+b') as file:
            while True:
                pos = file.tell()
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    reg.activo = 0
                    file.seek(pos + 4)
                    file.write(reg.to_bytes())
                    print(f"Registro con ID {id} eliminado del archivo principal.")
                    return True
                # Buscar en auxiliar si hay puntero
                if reg.indice != -1 and reg.filetype == 'a':
                    deleted = self._delete_aux(id, reg.indice)
                    if deleted:
                        return True
        print(f"Registro con ID {id} no encontrado.")
        return False

    def _delete_aux(self, id, start_index):
        with open(self.auxfile, 'r+b') as aux:
            current_index = start_index
            while current_index != -1:
                pos = current_index * (4 + RECORD_SIZE)
                aux.seek(pos)
                index_data = aux.read(4)
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.id == id and reg.activo == 1:
                    reg.activo = 0
                    aux.seek(pos + 4)
                    aux.write(reg.to_bytes())
                    print(f"Registro con ID {id} eliminado del archivo auxiliar.")
                    return True
                current_index = reg.indice if reg.filetype == 'a' else -1
        return False


    def search_range(self, min_id, max_id):
        resultados = []
        with open(self.filename, 'rb') as file:
            while True:
                index_data = file.read(4)
                data = file.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1 and min_id <= reg.id <= max_id:
                    resultados.append(reg)
                # Buscar en auxiliar si hay puntero
                if reg.indice != -1 and reg.filetype == 'a':
                    aux_regs = self._search_aux_range(min_id, max_id, reg.indice)
                    resultados.extend(aux_regs)
        return resultados

    def _search_aux_range(self, min_id, max_id, start_index):
        encontrados = []
        with open(self.auxfile, 'rb') as aux:
            current_index = start_index
            while current_index != -1:
                pos = current_index * (4 + RECORD_SIZE)
                aux.seek(pos)
                index_data = aux.read(4)
                data = aux.read(RECORD_SIZE)
                if not data:
                    break
                reg = Venta.from_bytes(data)
                if reg.activo == 1 and min_id <= reg.id <= max_id:
                    encontrados.append(reg)
                current_index = reg.indice if reg.filetype == 'a' else -1
        return encontrados



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

