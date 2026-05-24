"""
Parser para archivos Excel/CSV de ranking.
Mucho más preciso y rápido que OCR.
"""

from typing import List, Dict
import pandas as pd
import io


def parse_ranking_file(file_bytes: bytes, filename: str) -> List[Dict]:
    """
    Parsea un archivo Excel/CSV con datos del ranking.
    
    Formatos aceptados:
    - Excel: .xlsx, .xls
    - CSV: .csv (separado por comas o punto y coma)
    
    Columnas esperadas (cualquier orden, case-insensitive):
    - Rank / Ranking / Position
    - Alliance / Tag / Clan
    - Name / Player / Nombre
    - Score / Points / Puntos
    
    Returns:
        Lista de dicts con keys: rank, alliance, name, score
    """
    print(f"[Parser] Procesando archivo: {filename} ({len(file_bytes)} bytes)")
    
    try:
        # Detectar tipo de archivo
        if filename.endswith('.csv'):
            # Intentar con diferentes separadores
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8')
            except:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), sep=';', encoding='utf-8')
                except:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding='latin-1')
        
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_bytes))
        
        else:
            print(f"[Parser] X Formato no soportado: {filename}")
            return []
        
        print(f"[Parser] DataFrame cargado: {len(df)} filas, columnas: {list(df.columns)}")
        
        # Mapear columnas (case-insensitive)
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            if col_lower in ['rank', 'ranking', 'position', 'pos', '#']:
                col_map['rank'] = col
            elif col_lower in ['alliance', 'tag', 'clan', 'alianza']:
                col_map['alliance'] = col
            elif col_lower in ['name', 'player', 'nombre', 'jugador', 'governor']:
                col_map['name'] = col
            elif col_lower in ['score', 'points', 'puntos', 'pts']:
                col_map['score'] = col
        
        print(f"[Parser] Mapeo de columnas: {col_map}")
        
        # Validar que tenemos al menos rank
        if 'rank' not in col_map:
            print(f"[Parser] X Falta columna requerida: rank")
            return []
        
        # Si no hay alliance pero sí name/player, intentar extraer de formato [TAG]Name
        has_combined_format = False
        if 'alliance' not in col_map and 'name' in col_map:
            # Verificar si el formato es [TAG]Name
            sample = str(df[col_map['name']].iloc[0])
            if sample.startswith('[') and ']' in sample:
                has_combined_format = True
                print(f"[Parser] OK Detectado formato combinado [TAG]Name en columna '{col_map['name']}'")
        
        # Validar que tenemos datos suficientes
        if not has_combined_format and 'alliance' not in col_map:
            print(f"[Parser] X Falta columna 'alliance' o formato [TAG]Name")
            return []
        
        # Extraer datos
        entries = []
        for idx, row in df.iterrows():
            try:
                rank = int(row[col_map['rank']])
                
                # Procesar alliance y name según el formato
                if has_combined_format:
                    # Formato [TAG]Name
                    full_text = str(row[col_map['name']]).strip()
                    
                    if full_text.startswith('[') and ']' in full_text:
                        # Extraer tag y nombre
                        end_bracket = full_text.index(']')
                        alliance = full_text[1:end_bracket].strip().upper()
                        name = full_text[end_bracket+1:].strip()
                        
                        # Validar que el nombre no esté vacío
                        if not name or name.lower() == 'nan':
                            name = f"Player_{rank}"  # Nombre por defecto basado en rank
                    else:
                        # Fallback si no tiene formato esperado
                        alliance = 'UNKNOWN'
                        name = full_text
                else:
                    # Formato separado
                    alliance = str(row[col_map['alliance']]).strip().upper()
                    # Limpiar tags: quitar corchetes si están presentes
                    alliance = alliance.replace('[', '').replace(']', '').strip()
                    
                    # Nombre (opcional)
                    name = 'Unknown'
                    if 'name' in col_map:
                        name = str(row[col_map['name']]).strip()
                        if name.lower() == 'nan':
                            name = 'Unknown'
                
                if not alliance or alliance == 'NAN' or alliance == 'UNKNOWN':
                    continue
                
                # Score (opcional)
                score = None
                if 'score' in col_map:
                    try:
                        score = int(row[col_map['score']])
                    except:
                        pass
                
                # Validar rank en rango 1-100
                if 1 <= rank <= 100:
                    entries.append({
                        'rank': rank,
                        'alliance': alliance,
                        'name': name,
                        'score': score
                    })
            
            except Exception as e:
                print(f"[Parser] ! Error en fila {idx}: {e}")
                continue
        
        print(f"[Parser] OK Extraidas {len(entries)} entradas validas")
        
        # Ordenar por rank
        entries.sort(key=lambda e: e['rank'])
        return entries
        
    except Exception as e:
        print(f"[Parser] X Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
