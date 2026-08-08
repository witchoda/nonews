"""Generate 250 realistic fake Mexican news articles for dashboard visualization testing."""
import random
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

from nonews.database import get_session, init_db
from nonews.models import Article

init_db()

TITLES_BY_CATEGORY = {
    "politics": [
        ("Morena impulsa reforma para reducir senadores plurinominales", "negative", "national"),
        ("Sheinbaum anuncia gira por estados del sureste para verificar programas sociales", "neutral", "sureste"),
        ("Gobierno federal presenta plan nacional de austeridad 2027", "neutral", "national"),
        ("Senado aprueba en comisiones dictamen sobre consulta popular", "neutral", "national"),
        ("Opposition acusa al gobierno de opacidad en gasto público", "negative", "national"),
        ("Gobernador de Morelos firma convenio con la federación para obra pública", "positive", "Morelos"),
        ("Diputados debaten iniciativa para regular redes sociales en campañas", "neutral", "national"),
        ("Presidente recibe a embajadores de la Unión Europea en Palacio Nacional", "positive", "CDMX"),
        ("Congreso de Jalisco aprueba reforma al sistema de pensiones local", "positive", "Jalisco"),
        ("SCJN atrae controversia sobre ley de aguas de Nuevo León", "neutral", "Nuevo León"),
        ("Partidos políticos no logran acuerdo para designar al nuevo consejero del INE", "negative", "national"),
        ("Gobierno de CDMX lanza programa de apoyo a adultos mayores", "positive", "CDMX"),
        ("Secretario de Gobernación se reúne con mandatarios estatales en la Conago", "neutral", "national"),
        ("Camara de diputados aprueba presupuesto para ciencia y tecnología", "positive", "national"),
        ("Fiscalía investiga desvío de recursos en gobierno de Tamaulipas", "negative", "Tamaulipas"),
    ],
    "economy": [
        ("Banxico mantiene tasa de interés en 7.5% ante presiones inflacionarias", "negative", "national"),
        ("Peso mexicano se fortalece frente al dólar y cotiza en 16.80", "positive", "national"),
        ("Inversión extranjera directa crece 12% en el primer semestre", "positive", "national"),
        ("IMSS reporta déficit de 15,000 millones en primer trimestre", "negative", "national"),
        ("Exportaciones manufactureras de Monterrey alcanzan récord histórico", "positive", "Nuevo León"),
        ("Profeco verifica precios de la canasta básica en 500 tiendas del país", "neutral", "national"),
        ("Nearshoring impulsa creación de 80,000 empleos industriales en Querétaro", "positive", "Querétaro"),
        ("SAT anuncia nueva plataforma digital para declaración anual", "neutral", "national"),
        ("Sector agroexportador de Sinaloa reporta pérdidas por sequía", "negative", "Sinaloa"),
        ("Turismo en Quintana Roo crece 18% respecto al año anterior", "positive", "Quintana Roo"),
        ("Gobierno federal elimina pago de tenencia vehicular en 10 estados", "positive", "national"),
        (" Inflación subyacente baja a 4.2% anual, la menor en dos años", "positive", "national"),
        ("Comerciantes del Centro Histórico de CDMX reportan caída en ventas", "negative", "CDMX"),
        ("México se convierte en el primer socio comercial de Brasil en Latam", "positive", "national"),
        ("PyMES de Puebla pierden millones por falta de acceso a créditos bancarios", "negative", "Puebla"),
    ],
    "security": [
        ("Estrategia de seguridad en Zacatecas deja 200 detenciones en un mes", "neutral", "Zacatecas"),
        ("Gobierno federal despliega Guardia Nacional en carreteras de Michoacán", "negative", "Michoacán"),
        ("Operativo conjunto en Tijuana resulta en decomiso de 500 kg de narcóticos", "positive", "Baja California"),
        ("Levantón en Guadalajara deja 3 personas desaparecidas", "negative", "Jalisco"),
        ("Secretario de Seguridad presenta plan de vigilancia con drones en CDMX", "neutral", "CDMX"),
        ("Violencia en Durango obliga a cerrar 15 escuelas en zona rural", "negative", "Durango"),
        ("Marina intercepta narcolancha en costas de Oaxaca", "positive", "Oaxaca"),
        ("Ejecutan a candidato a alcaldía en Guerrero durante acto de campaña", "negative", "Guerrero"),
        ("Gobierno de Veracruz instala 500 cámaras de videovigilancia en Xalapa", "positive", "Veracruz"),
        ("Detienen a líder de célula criminal en operativo en Sonora", "positive", "Sonora"),
        ("Bloqueos en carreteras de Chiapas dejan saldo de 10 horas sin circulación", "negative", "Chiapas"),
        ("FGR desarticula red de extorsión telefónica que operaba desde CDMX", "positive", "CDMX"),
        ("Incremento de 30% en homicidios en Estado de México durante julio", "negative", "México"),
        ("Nuevo protocolo de seguridad escolar se implementa en Coahuila", "neutral", "Coahuila"),
        ("Rescatan a 12 migrantes secuestrados en Tamaulipas", "positive", "Tamaulipas"),
    ],
    "energy": [
        ("Pemex reporta reducción de 15% en robo de combustible gracias a monitoreo", "positive", "national"),
        ("CFE inaugura planta solar en Sonora con capacidad para 200,000 hogares", "positive", "Sonora"),
        ("Gasolineras de Hidalgo aumentan precios hasta 50 centavos por litro", "negative", "Hidalgo"),
        ("México firma acuerdo con Argentina para intercambio de tecnología energética", "positive", "national"),
        ("Sistema eléctrico nacional opera sin apagones por tercer mes consecutivo", "positive", "national"),
        ("Trabajadores de Pemex en Tabasco amenazan con paro por condiciones laborales", "negative", "Tabasco"),
        ("Energía eólica en Oaxaca alcanza 30% de la generación local", "positive", "Oaxaca"),
        ("Gobierno anuncia subsidio para paneles solares en viviendas de interés social", "positive", "national"),
        ("Derrame de hidrocarburo en río de Veracruz afecta a 3 comunidades", "negative", "Veracruz"),
        ("CFE reduce tarifas eléctricas para usuarios de bajo consumo en verano", "positive", "national"),
    ],
    "education": [
        ("UNAM abre 5,000 plazas adicionales para aspirantes de nuevo ingreso", "positive", "CDMX"),
        ("SEP anuncia que libros de texto gratuitos llegarán a tiempo en septiembre", "neutral", "national"),
        ("Maestros de Oaxaca mantienen paro laboral por mejoras salariales", "negative", "Oaxaca"),
        ("IPN desarrolla programa de becas para estudiantes de ingeniería", "positive", "CDMX"),
        ("Deserción escolar en secundaria crece 8% en zonas rurales de Guerrero", "negative", "Guerrero"),
        ("Alumnos de preparatoria en Yucatán ganan competencia nacional de robótica", "positive", "Yucatán"),
        ("Universidades de Puebla firman convenio de intercambio con Canadá", "positive", "Puebla"),
        ("Investigadores del Cinvestav desarrollan vacuna contra dengue más efectiva", "positive", "CDMX"),
        ("Padres de familia en Edomex protestan por falta de maestros bilingües", "negative", "México"),
        ("Programa de alimentación escolar beneficia a 2 millones de niños", "positive", "national"),
    ],
    "health": [
        ("IMSS-Bienestar abre 30 nuevas clínicas en comunidades rurales", "positive", "national"),
        ("Jornada de vacunación contra sarampión alcanza 95% de cobertura en CDMX", "positive", "CDMX"),
        ("Hospital General de León reporta desabasto de medicamentos oncológicos", "negative", "Guanajuato"),
        ("SSA detecta brote de dengue en 5 municipios de Colima", "negative", "Colima"),
        ("México recibe donación de 500,000 dosis de vacuna contra influenza", "positive", "national"),
        ("Médicos del ISSSTE inician movimiento por mejora de salarios", "negative", "national"),
        ("Nuevo hospital regional en Tlaxcala atenderá a 100,000 pacientes al año", "positive", "Tlaxcala"),
        ("Alerta sanitaria por consumo de alcohol adulterado en Baja California", "negative", "Baja California"),
        ("Investigadores de la UNAM desarrollan prueba rápida para cáncer de mama", "positive", "CDMX"),
        ("Campaña de donación de órganos en Jalisco salva a 45 pacientes", "positive", "Jalisco"),
    ],
    "infrastructure": [
        ("Tren Maya reporta 2 millones de pasajeros en su primer año de operación", "positive", "sureste"),
        ("Gobierno federal licita construcción del nuevo aeropuerto de Tulum", "neutral", "Quintana Roo"),
        ("Puente vehicular en Puebla colapsa tras lluvias intensas", "negative", "Puebla"),
        ("Corredor Interoceánico avanza con 60% de obra completada", "positive", "Veracruz"),
        ("Metro de CDMX línea 12 requiere mantenimiento mayor tras sismo", "negative", "CDMX"),
        ("Inauguran libramiento carretero en Durango que reduce 2 horas de viaje", "positive", "Durango"),
        ("Construcción de presa en Nayarit beneficiará a 500,000 habitantes", "positive", "Nayarit"),
        ("Bacheo en calles de Nezahualcóyotl genera quejas de vecinos", "negative", "México"),
        ("Aeropuerto de Guadalajara amplía terminal internacional", "positive", "Jalisco"),
        ("Gobierno de Aguascalientes invierte en modernización del transporte público", "positive", "Aguascalientes"),
    ],
    "international": [
        ("México y Canadá firman acuerdo de cooperación en materia automotriz", "positive", "national"),
        ("Trump amenaza con aranceles del 25% a productos mexicanos", "negative", "national"),
        ("Caravana migrante de 3,000 centroamericanos cruza Chiapas rumbo al norte", "neutral", "Chiapas"),
        ("México condena ataque militar en Oriente Medio y pide diálogo", "neutral", "national"),
        ("Remesas a México alcanzan récord de 5,800 millones de dólares en junio", "positive", "national"),
        ("Deportación masiva de mexicanos desde EUA genera crisis humanitaria", "negative", "national"),
        ("T-MEC panel resuelve disputa a favor de exportadores mexicanos de tomate", "positive", "national"),
        ("Cumbre del G20 aborda crisis climática con participación de Sheinbaum", "neutral", "international"),
        ("Embajada de México en Francia promueve inversión turística", "positive", "international"),
        ("Organizaciones internacionales critican política migratoria de México", "negative", "national"),
    ],
    "environment": [
        ("Huracán categoría 4 se aproxima a las costas de Baja California Sur", "negative", "Baja California Sur"),
        ("Deforestación en la Sierra Gorda de Querétaro alcanza nivel crítico", "negative", "Querétaro"),
        ("Programa de reforestación en CDMX planta 100,000 árboles en un año", "positive", "CDMX"),
        ("Contingencia ambiental se activa en Monterrey por calidad del aire", "negative", "Nuevo León"),
        ("Avistamiento de ballenas jorobadas en Puerto Vallarta rompe récord", "positive", "Jalisco"),
        ("Sequía en Sonora obliga a racionar agua en 8 municipios", "negative", "Sonora"),
        ("México reduce 12% sus emisiones de CO2 respecto al año anterior", "positive", "national"),
        ("Derrame de aguas negras en lago de Pátzcuaro afecta ecosistema", "negative", "Michoacán"),
        ("Áreas naturales protegidas de Campeche reciben certificación internacional", "positive", "Campeche"),
        ("Lluvias atípicas en Yucatán dañan cultivos de maíz", "negative", "Yucatán"),
    ],
    "technology": [
        ("Startups mexicanas captan 800 millones de dólares en inversión durante 2026", "positive", "national"),
        ("Gobierno lanza app para denunciar corrupción en trámites federales", "positive", "national"),
        ("Ciberataque a banco mexicano expone datos de 2 millones de clientes", "negative", "national"),
        ("Guadalajara se consolida como hub tecnológico de Latinoamérica", "positive", "Jalisco"),
        ("México ocupa el lugar 15 en ranking mundial de conectividad 5G", "neutral", "national"),
        ("Empresas de inteligencia artificial se instalan en Parque Tecnológico de Querétaro", "positive", "Querétaro"),
        ("Fallas en plataforma del SAT impiden declaraciones fiscales", "negative", "national"),
        ("Programa de digitalización llega a 5,000 escuelas rurales en México", "positive", "national"),
        ("Hackers rusos atacan infraestructura crítica del sistema eléctrico mexicano", "negative", "national"),
        ("UNAM desarrolla robot cirujano con tecnología 100% mexicana", "positive", "CDMX"),
    ],
    "culture": [
        ("Festival Cervantino 2026 rompe récord de asistencia con 400,000 visitantes", "positive", "Guanajuato"),
        ("Museo Nacional de Antropología exhibe pieza maya encontrada en Calakmul", "positive", "CDMX"),
        ("Película mexicana gana premio en Festival de Cannes", "positive", "national"),
        ("Escándalo por censura a artista en Museo de Arte Moderno de CDMX", "negative", "CDMX"),
        ("Feria del Libro de Guadalajara anuncia programa con 300 autores", "positive", "Jalisco"),
        ("Mariachi mexicano es declarado Patrimonio Inmaterial de la Humanidad por UNESCO", "positive", "national"),
        ("Comunidad artística de Oaxaca protesta por recorte a fondos culturales", "negative", "Oaxaca"),
        ("Lucha libre mexicana celebra 70 años de la Arena México", "positive", "CDMX"),
        ("Gastronomía mexicana posiciona a Puebla como destino culinario mundial", "positive", "Puebla"),
        ("Ballet Folklórico de México gira por 15 ciudades de Europa", "positive", "national"),
    ],
    "justice": [
        ("FGR obtiene sentencia de 40 años contra líder del cartel del norte", "positive", "national"),
        ("SCJN declara inconstitucional ley de movilidad de Nuevo León", "neutral", "Nuevo León"),
        ("Liberan a periodista detenido arbitrariamente en Tabasco", "positive", "Tabasco"),
        ("CNDH emite recomendación al gobierno de Colima por violaciones a DDHH", "negative", "Colima"),
        ("Juez vincula a proceso a exgobernador de Tamaulipas por desvío de recursos", "positive", "Tamaulipas"),
        ("Impunidad en México alcanza 92% según estudio de la UNAM", "negative", "national"),
        ("Nuevo sistema de justicia penal acusatorio cumple 10 años con resultados mixtos", "neutral", "national"),
        ("Madres buscadoras de Sonora encuentran 15 cuerpos en fosa clandestina", "negative", "Sonora"),
        ("Reforma judicial reduce tiempos de proceso penal en un 40%", "positive", "national"),
        ("Defensoría pública de Veracruz recibe premio internacional por transparencia", "positive", "Veracruz"),
    ],
}


def generate_fake_articles(count=250):
    articles = []
    base_date = datetime(2026, 8, 8)
    
    all_combos = []
    for cat, items in TITLES_BY_CATEGORY.items():
        for title, sentiment, region in items:
            all_combos.append((cat, title, sentiment, region))
    
    random.seed(42)
    selected = random.choices(all_combos, k=count)
    
    for i, (cat, title, sentiment, region) in enumerate(selected):
        pub_date = base_date - timedelta(hours=random.randint(0, 720))
        articles.append({
            "source_name": "Generado",
            "title": title,
            "url": f"https://fake-news.example.com/article-{1000+i}",
            "author": None,
            "published_at": pub_date,
            "summary": "",
            "categories": [cat],
            "content_depth": "feed",
            "sentiment": sentiment,
            "affected_region": region,
            "opinion": f"{sentiment} para {region}: {title[:60]}",
            "analyzed": True,
            "is_fake": True,
        })
    
    return articles


if __name__ == "__main__":
    session = get_session()
    articles = generate_fake_articles(250)
    
    saved = 0
    for art_data in articles:
        art = Article(**art_data)
        session.add(art)
        saved += 1
    
    session.commit()
    session.close()
    print(f"Inserted {saved} fake articles")
