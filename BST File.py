import struct
import csv
import os


# Formato para el registro (ID, Nombre producto, Cantidad vendida, Precio unitario, Fecha de venta)
FORMAT = 'i30sif10sii'  # i (int), 30s (string 30 bytes), i (int), f (float), 10s (string 10 bytes)
HEADER_FORMAT = 'i'  # Header de 4 bytes (almacena cantidad de registros)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
RECORD_SIZE = struct.calcsize(FORMAT)

class Venta:
    def __init__(self, id_venta, nombre_producto, cantidad_vendida, precio_unitario, fecha_venta, left=-1,right=-1):
        self.id_venta = id_venta
        self.nombre_producto = nombre_producto.encode('utf-8')[:30].ljust(30, b' ')
        self.cantidad_vendida = cantidad_vendida
        self.precio_unitario = precio_unitario
        self.fecha_venta = fecha_venta.encode('utf-8')[:10].ljust(10, b' ')
        self.left = left
        self.right=right

    def __str__(self):
        return (f"ID Venta: {self.id_venta} | Producto: {self.nombre_producto.decode().strip()} "
                f"| Cantidad: {self.cantidad_vendida} | Precio: {self.precio_unitario} "
                f"| Fecha: {self.fecha_venta.decode().strip()} | left: {self.left} | right: {self.right}")


# Función para cargar datos desde un archivo CSV
def cargar_datos_desde_csv(archivo_csv):
    ventas = []
    with open(archivo_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Omitir la cabecera
        for row in reader:
            id_venta = int(row[0])
            nombre_producto = row[1]
            cantidad_vendida = int(row[2])
            precio_unitario = float(row[3])
            fecha_venta = row[4]
            venta = Venta(id_venta, nombre_producto, cantidad_vendida, precio_unitario, fecha_venta)
            ventas.append(venta)
    return ventas

# Clase para manejar el archivo AVL
class ArchivoAVL:
    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(filename):
            with open(filename, 'wb') as f:
                f.write(struct.pack(HEADER_FORMAT, 0))  # Inicializar con 0 registros
    
    def insert(record):
        
    def leer():
        
    def search(key):
        
    
    def remove(key):
        
    
    def rangeSearch(init_key, end_key):
        

    
# Código de prueba
if __name__ == "__main__":
    archivo = ArchivoAVL("ventas.dat")
    
    # Insertar ventas
    archivo.insert(Venta(1, "Producto A", 10, 5.5, "2024-07-01"))
    archivo.insert(Venta(2, "Producto B", 5, 10.0, "2024-07-02"))
    archivo.insert(Venta(3, "Producto C", 7, 8.75, "2024-07-03"))
    
    # Leer todas las ventas
    print("Ventas registradas:")
    for venta in archivo.leer():
        print(venta)
    
    # Buscar una venta específica
    print("\nBuscando venta con ID 2:")
    print(archivo.search(2))
    
    # Eliminar una venta
    print("\nEliminando venta con ID 2")
    archivo.remove(2)
    
    # Verificar eliminación
    print("\nVentas después de eliminación:")
    for venta in archivo.leer():
        print(venta)
    
    # Búsqueda por rango
    print("\nBuscando ventas con ID entre 1 y 3:")
    for venta in archivo.rangeSearch(1, 3):
        print(venta)

