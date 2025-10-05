#!/usr/bin/env python3
"""
Satellite Analysis System
NASA Space App Challenge 2025

This system allows:
1. Get satellite data from Celestrak using Skyfield
2. Search satellites by name
3. Calculate orbits and future positions
4. Predict possible collisions in the next 4 days
5. Visualize orbital trajectories

Author: NASA Space App Team
Date: October 2025
"""

import requests
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import os
from skyfield.api import load, EarthSatellite
from skyfield.timelib import Time
import pandas as pd
from typing import List, Dict, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Advanced scientific imports
try:
    from scipy.special import erfc
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ SciPy not available - using alternative methods for probability")

# Imports for 3D visualization
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class SatelliteAnalyzer:
    """
    Main class for satellite analysis using Skyfield and Celestrak data
    """
    
    def __init__(self):
        """Initialize the satellite analyzer"""
        self.ts = load.timescale()
        self.satellites = {}
        self.tle_data = {}
        self.earth = load('de421.bsp')['earth']
        
        # Initialize new advanced components
        self.realistic_propagator = RealisticOrbitPropagator()
        self.advanced_collision_analyzer = AdvancedCollisionAnalyzer()
        self.uncertainty_model = UncertaintyModel()
        
        print("🛰️  Initializing Satellite Analysis System...")
        print("🔬 Advanced components loaded:")
        print("   ✅ Realistic orbital propagator (J2 + drag)")
        print("   ✅ Probabilistic collision analyzer")
        print("   ✅ Non-linear uncertainty model")
        
    def download_tle_data(self, tle_url: str = None) -> bool:
        """
        Download TLE (Two-Line Elements) data from Celestrak
        
        Args:
            tle_url: Custom URL for TLE data
            
        Returns:
            bool: True if download was successful
        """
        try:
            # URLs for different satellite categories from Celestrak
            urls = {
                'active': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle',
                'stations': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle',
                'weather': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle',
                'communications': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle',
                'navigation': 'https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle'
            }
            
            if tle_url:
                urls['custom'] = tle_url
                
            print("📡 Downloading TLE data from Celestrak...")
            
            all_satellites = {}
            for category, url in urls.items():
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    
                    # Parse TLE data
                    lines = response.text.strip().split('\n')
                    i = 0
                    while i < len(lines) - 2:
                        if lines[i].strip() and not lines[i].startswith('#'):
                            name = lines[i].strip()
                            line1 = lines[i + 1].strip()
                            line2 = lines[i + 2].strip()
                            
                            if line1.startswith('1 ') and line2.startswith('2 '):
                                # Create satellite using Skyfield
                                satellite = EarthSatellite(line1, line2, name, self.ts)
                                all_satellites[name] = {
                                    'satellite': satellite,
                                    'line1': line1,
                                    'line2': line2,
                                    'category': category
                                }
                        i += 3
                        
                    print(f"   ✅ {category}: {len([s for s in all_satellites.values() if s['category'] == category])} satellites")
                    
                except Exception as e:
                    print(f"   ❌ Error downloading {category}: {str(e)}")
                    continue
            
            self.satellites = all_satellites
            print(f"🎯 Total satellites loaded: {len(self.satellites)}")
            return True
            
        except Exception as e:
            print(f"❌ Error downloading TLE data: {str(e)}")
            return False
    
    def export_satellites_list(self, filename: str = "available_satellites.txt") -> bool:
        """
        Export list of all available satellites to a text file
        
        Args:
            filename: Name of the file to create
            
        Returns:
            bool: True if export was successful
        """
        try:
            if not self.satellites:
                print("❌ No satellites loaded. Run download_tle_data() first.")
                return False
            
            # Organize satellites by category
            satellites_by_category = {}
            for name, data in self.satellites.items():
                category = data['category']
                if category not in satellites_by_category:
                    satellites_by_category[category] = []
                satellites_by_category[category].append(name)
            
            # Sort satellites alphabetically within each category
            for category in satellites_by_category:
                satellites_by_category[category].sort()
            
            # Create the text file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("LIST OF AVAILABLE SATELLITES\n")
                f.write("Satellite Analysis System - NASA Space App Challenge 2025\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generation date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total satellites: {len(self.satellites)}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write summary by category
                f.write("SUMMARY BY CATEGORY:\n")
                f.write("-" * 40 + "\n")
                total_count = 0
                for category, sat_list in satellites_by_category.items():
                    count = len(sat_list)
                    total_count += count
                    f.write(f"{category.capitalize():20s}: {count:5d} satellites\n")
                f.write("-" * 40 + "\n")
                f.write(f"{'TOTAL':20s}: {total_count:5d} satellites\n\n")
                
                # Write detailed list by category
                for category, sat_list in satellites_by_category.items():
                    f.write("=" * 80 + "\n")
                    f.write(f"CATEGORY: {category.upper()}\n")
                    f.write(f"Total in this category: {len(sat_list)} satellites\n")
                    f.write("=" * 80 + "\n")
                    
                    for i, sat_name in enumerate(sat_list, 1):
                        f.write(f"{i:4d}. {sat_name}\n")
                    
                    f.write("\n")
                
                # Add complete alphabetical list
                f.write("=" * 80 + "\n")
                f.write("COMPLETE ALPHABETICAL LIST\n")
                f.write("=" * 80 + "\n")
                
                all_satellites = sorted(self.satellites.keys())
                for i, sat_name in enumerate(all_satellites, 1):
                    category = self.satellites[sat_name]['category']
                    f.write(f"{i:5d}. {sat_name:<50s} [{category}]\n")
                
                # Add useful information at the end
                f.write("\n" + "=" * 80 + "\n")
                f.write("USAGE INSTRUCTIONS:\n")
                f.write("=" * 80 + "\n")
                f.write("1. Copy the exact name of the satellite you want to analyze\n")
                f.write("2. Paste it in the program when the name is requested\n")
                f.write("3. Names are case sensitive\n")
                f.write("4. Use Ctrl+F to search for specific satellites in this file\n\n")
                
                f.write("EXAMPLES OF INTERESTING SATELLITES:\n")
                f.write("-" * 40 + "\n")
                
                # Search for some interesting satellites as examples
                interesting_examples = []
                search_terms = ["ISS", "HUBBLE", "NOAA", "GPS", "STARLINK", "GOES"]
                
                for term in search_terms:
                    matches = [name for name in all_satellites if term in name.upper()]
                    if matches:
                        interesting_examples.append(f"• {matches[0]} (search: '{term}')")
                
                for example in interesting_examples:
                    f.write(f"{example}\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write("Explore the cosmos, one satellite at a time! 🛰️🌌\n")
                f.write("=" * 80 + "\n")
            
            print(f"✅ Satellite list exported successfully:")
            print(f"   📁 File: {filename}")
            print(f"   🛰️  Total satellites: {len(self.satellites)}")
            print(f"   📂 Categories: {len(satellites_by_category)}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting satellite list: {str(e)}")
            return False
    
    def search_satellite(self, search_term: str) -> List[str]:
        """
        Search satellites by name
        
        Args:
            search_term: Search term
            
        Returns:
            List[str]: List of matching satellite names
        """
        search_term = search_term.lower()
        matches = []
        
        for name in self.satellites.keys():
            if search_term in name.lower():
                matches.append(name)
                
        return sorted(matches)
    
    def get_popular_satellites(self) -> Dict[str, List[str]]:
        """
        Get a list of popular satellites organized by category
        
        Returns:
            Dict: Dictionary with categories and popular satellites
        """
        popular_categories = {
            'Space Stations': ['ISS', 'ZARYA', 'TIANGONG'],
            'Space Telescopes': ['HUBBLE', 'SPITZER', 'CHANDRA'],
            'Weather Satellites': ['NOAA', 'GOES', 'METEOSAT'],
            'GPS Navigation': ['GPS', 'NAVSTAR', 'GLONASS'],
            'Communications': ['STARLINK', 'INTELSAT', 'IRIDIUM'],
            'Earth Observation': ['LANDSAT', 'AQUA', 'TERRA', 'SENTINEL']
        }
        
        found_satellites = {}
        
        for category, search_terms in popular_categories.items():
            found_satellites[category] = []
            for term in search_terms:
                matches = self.search_satellite(term)
                if matches:
                    # Add first 3 matches of each term
                    found_satellites[category].extend(matches[:3])
            
            # Remove duplicates and limit to 5 per category
            found_satellites[category] = list(dict.fromkeys(found_satellites[category]))[:5]
        
        return found_satellites
    
    def suggest_satellites(self, partial_name: str) -> List[str]:
        """
        Suggest satellites based on partial name
        
        Args:
            partial_name: Partial satellite name
            
        Returns:
            List[str]: List of suggestions
        """
        if len(partial_name) < 2:
            return []
        
        partial_name = partial_name.lower()
        suggestions = []
        
        # Search for exact matches at the beginning of the name
        for name in self.satellites.keys():
            if name.lower().startswith(partial_name):
                suggestions.append(name)
        
        # If not enough, search for matches anywhere in the name
        if len(suggestions) < 10:
            for name in self.satellites.keys():
                if partial_name in name.lower() and name not in suggestions:
                    suggestions.append(name)
        
        return sorted(suggestions)[:15]  # Limit to 15 suggestions
    
    def browse_satellites_by_category(self) -> Dict[str, List[str]]:
        """
        Browse satellites organized by category
        
        Returns:
            Dict: Satellites organized by category with samples
        """
        satellites_by_category = {}
        
        for name, data in self.satellites.items():
            category = data['category']
            if category not in satellites_by_category:
                satellites_by_category[category] = []
            satellites_by_category[category].append(name)
        
        # Sort and limit for easy browsing
        for category in satellites_by_category:
            satellites_by_category[category] = sorted(satellites_by_category[category])
        
        return satellites_by_category
    
    def show_satellite_examples(self) -> None:
        """
        Show examples of interesting satellites with description
        """
        examples = {
            "🏠 Space Stations": {
                "search_terms": ["ISS", "ZARYA", "TIANGONG"],
                "description": "Manned orbital laboratories"
            },
            "🔭 Space Telescopes": {
                "search_terms": ["HUBBLE", "SPITZER", "KEPLER"],
                "description": "Astronomical observatories in space"
            },
            "🌤️ Weather Satellites": {
                "search_terms": ["NOAA", "GOES", "METEOSAT"],
                "description": "Climate and weather monitoring"
            },
            "🗺️ GPS Navigation": {
                "search_terms": ["GPS", "NAVSTAR", "GALILEO"],
                "description": "Global positioning systems"
            },
            "📡 Communications": {
                "search_terms": ["STARLINK", "IRIDIUM", "INTELSAT"],
                "description": "Internet and telecommunications"
            },
            "🌍 Earth Observation": {
                "search_terms": ["LANDSAT", "AQUA", "TERRA"],
                "description": "Environmental and resource monitoring"
            }
        }
        
        print("\n🌟 EXAMPLES OF INTERESTING SATELLITES:")
        print("=" * 60)
        
        for category, info in examples.items():
            print(f"\n{category}")
            print(f"📝 {info['description']}")
            found_examples = []
            
            for term in info['search_terms']:
                matches = self.search_satellite(term)
                if matches:
                    found_examples.extend(matches[:2])  # Maximum 2 per term
            
            # Show unique examples
            unique_examples = list(dict.fromkeys(found_examples))[:3]
            for i, example in enumerate(unique_examples, 1):
                print(f"   {i}. {example}")
            
            if not unique_examples:
                print("   (No examples found in current data)")
        
        print(f"\n💡 TIP: Use option 1 to search for any of these names")
        print(f"🔍 Example: search 'ISS' to find the International Space Station")
    
    def smart_search(self, search_term: str) -> Dict:
        """
        Smart search that provides results and suggestions
        
        Args:
            search_term: Search term
            
        Returns:
            Dict: Detailed results with suggestions
        """
        results = {
            'exact_matches': [],
            'partial_matches': [],
            'suggestions': [],
            'category_matches': {},
            'total_found': 0
        }
        
        if not search_term or len(search_term) < 2:
            return results
        
        search_lower = search_term.lower()
        
        # Search for exact matches
        for name in self.satellites.keys():
            name_lower = name.lower()
            if search_lower == name_lower:
                results['exact_matches'].append(name)
            elif search_lower in name_lower:
                results['partial_matches'].append(name)
        
        # Organize by category
        for name in results['partial_matches']:
            category = self.satellites[name]['category']
            if category not in results['category_matches']:
                results['category_matches'][category] = []
            results['category_matches'][category].append(name)
        
        # Generate suggestions if there are few results
        if len(results['partial_matches']) < 10:
            results['suggestions'] = self.suggest_satellites(search_term)
        
        results['total_found'] = len(results['exact_matches']) + len(results['partial_matches'])
        
        return results
    
    def get_satellite_info(self, satellite_name: str) -> Optional[Dict]:
        """
        Get detailed information about a satellite
        
        Args:
            satellite_name: Name of the satellite
            
        Returns:
            Dict: Satellite information or None if not found
        """
        if satellite_name not in self.satellites:
            return None
            
        sat_data = self.satellites[satellite_name]
        satellite = sat_data['satellite']
        
        # Current time
        now = self.ts.now()
        
        # Calculate current position
        geocentric = satellite.at(now)
        subpoint = geocentric.subpoint()
        
        # Extract orbital elements from TLE
        line1 = sat_data['line1']
        line2 = sat_data['line2']
        
        # Parse orbital elements
        inclination = float(line2[8:16])
        raan = float(line2[17:25])  # Right Ascension of Ascending Node
        eccentricity = float('0.' + line2[26:33])
        arg_perigee = float(line2[34:42])
        mean_anomaly = float(line2[43:51])
        mean_motion = float(line2[52:63])
        
        # Calculate orbital period
        period_minutes = 1440 / mean_motion  # minutes
        period_hours = period_minutes / 60
        
        # Calculate approximate altitude
        # Using Kepler's third law: n = sqrt(GM/a³)
        GM = 398600.4418  # km³/s²
        n_rad_per_sec = mean_motion * 2 * np.pi / 86400  # radians per second
        semi_major_axis = (GM / (n_rad_per_sec ** 2)) ** (1/3)
        
        altitude_km = semi_major_axis - 6371  # Earth radius approx
        
        info = {
            'name': satellite_name,
            'category': sat_data['category'],
            'current_position': {
                'latitude': subpoint.latitude.degrees,
                'longitude': subpoint.longitude.degrees,
                'altitude_km': subpoint.elevation.km
            },
            'orbital_elements': {
                'inclination_deg': inclination,
                'raan_deg': raan,
                'eccentricity': eccentricity,
                'argument_of_perigee_deg': arg_perigee,
                'mean_anomaly_deg': mean_anomaly,
                'mean_motion_rev_per_day': mean_motion,
                'period_hours': period_hours,
                'semi_major_axis_km': semi_major_axis,
                'approx_altitude_km': altitude_km
            },
            'tle_data': {
                'line1': line1,
                'line2': line2
            }
        }
        
        return info
    
    def calculate_future_positions(self, satellite_name: str, days_ahead: int = 180) -> List[Dict]:
        """
        Calculate future positions of the satellite
        
        Args:
            satellite_name: Name of the satellite
            days_ahead: Days into the future to calculate
            
        Returns:
            List[Dict]: Future positions of the satellite
        """
        try:
            if satellite_name not in self.satellites:
                print(f"❌ Satellite '{satellite_name}' not found in database")
                # Search for partial matches
                matches = [name for name in self.satellites.keys() if satellite_name.lower() in name.lower()]
                if matches:
                    print(f"💡 Did you mean any of these?")
                    for i, match in enumerate(matches[:5], 1):
                        print(f"   {i}. {match}")
                return []
                
            satellite = self.satellites[satellite_name]['satellite']
            print(f"✅ Calculating positions for: {satellite_name}")
            
            # Create timestamps for upcoming days
            start_time = self.ts.now()
            positions = []
            
            # Calculate positions every 12 hours
            total_points = days_ahead * 2  # Every 12 hours = 2 points per day
            print(f"📊 Calculating {total_points} positions for {days_ahead} days...")
            
            for hours in range(0, days_ahead * 24, 12):
                try:
                    t = self.ts.tt_jd(start_time.tt + hours / 24)
                    geocentric = satellite.at(t)
                    subpoint = geocentric.subpoint()
                    
                    positions.append({
                        'datetime': t.utc_datetime(),
                        'latitude': subpoint.latitude.degrees,
                        'longitude': subpoint.longitude.degrees,
                        'altitude_km': subpoint.elevation.km,
                        'x_km': geocentric.position.km[0],
                        'y_km': geocentric.position.km[1],
                        'z_km': geocentric.position.km[2]
                    })
                except Exception as calc_error:
                    print(f"⚠️  Error calculating position for hour {hours}: {calc_error}")
                    continue
                    
            print(f"✅ Successfully calculated {len(positions)} positions")
            return positions
            
        except Exception as e:
            print(f"❌ Error in calculate_future_positions: {str(e)}")
            return []
    
    def analyze_collision_risk(self, satellite1_name: str, satellite2_name: str = None, 
                             threshold_km: float = 10.0, days_ahead: int = 180) -> Dict:
        """
        Analyze collision risk between satellites
        
        Args:
            satellite1_name: First satellite
            satellite2_name: Second satellite (if None, analyzes against all)
            threshold_km: Minimum distance to consider risk
            days_ahead: Days to analyze into the future
            
        Returns:
            Dict: Collision risk analysis
        """
        if satellite1_name not in self.satellites:
            return {'error': f'Satellite {satellite1_name} not found'}
            
        sat1 = self.satellites[satellite1_name]['satellite']
        close_encounters = []
        
        # Determine satellites to analyze
        satellites_to_check = {}
        if satellite2_name:
            if satellite2_name in self.satellites:
                satellites_to_check[satellite2_name] = self.satellites[satellite2_name]
        else:
            # Analyze against a sample of satellites (first 100 for efficiency)
            sat_names = list(self.satellites.keys())[:100]
            for name in sat_names:
                if name != satellite1_name:
                    satellites_to_check[name] = self.satellites[name]
        
        print(f"🔍 Analyzing {len(satellites_to_check)} satellites for possible collisions...")
        
        # Analyze every 6 hours during the specified period
        for hours in range(0, days_ahead * 24, 6):
            t = self.ts.tt_jd(self.ts.now().tt + hours / 24)
            pos1 = sat1.at(t)
            
            for sat2_name, sat2_data in satellites_to_check.items():
                sat2 = sat2_data['satellite']
                pos2 = sat2.at(t)
                
                # Calculate distance between satellites
                distance_km = np.linalg.norm(
                    np.array(pos1.position.km) - np.array(pos2.position.km)
                )
                
                if distance_km < threshold_km:
                    close_encounters.append({
                        'datetime': t.utc_datetime(),
                        'satellite2': sat2_name,
                        'distance_km': distance_km,
                        'satellite1_pos': pos1.position.km,
                        'satellite2_pos': pos2.position.km
                    })
        
        # Calculate risk statistics
        risk_level = 'LOW'
        if close_encounters:
            min_distance = min(enc['distance_km'] for enc in close_encounters)
            if min_distance < 1.0:
                risk_level = 'CRITICAL'
            elif min_distance < 5.0:
                risk_level = 'HIGH'
            else:
                risk_level = 'MEDIUM'
        
        return {
            'satellite': satellite1_name,
            'analysis_period_days': days_ahead,
            'threshold_km': threshold_km,
            'close_encounters': close_encounters,
            'risk_level': risk_level,
            'total_encounters': len(close_encounters),
            'satellites_analyzed': len(satellites_to_check)
        }
    
    def advanced_collision_analysis(self, satellite1_name: str, satellite2_name: str = None, 
                                  threshold_km: float = 10.0, days_ahead: int = 7) -> Dict:
        """
        ADVANCED collision analysis with real statistical probability
        
        Includes:
        - Orbital perturbations (J2, atmospheric drag)
        - Uncertainty ellipsoids
        - Statistical collision probability
        - Uncertainty propagation
        
        Args:
            satellite1_name: First satellite
            satellite2_name: Second satellite (if None, analyzes against sample)
            threshold_km: Distance for detailed analysis
            days_ahead: Days to analyze
            
        Returns:
            Dict: Probabilistic collision analysis
        """
        try:
            if satellite1_name not in self.satellites:
                return {'error': f'Satellite {satellite1_name} not found'}
                
            sat1 = self.satellites[satellite1_name]['satellite']
            detailed_analysis = []
            
            # Determine satellites for analysis
            satellites_to_check = {}
            if satellite2_name:
                if satellite2_name in self.satellites:
                    satellites_to_check[satellite2_name] = self.satellites[satellite2_name]
            else:
                # Use smaller sample for detailed analysis
                sat_names = list(self.satellites.keys())[:20]
                for name in sat_names:
                    if name != satellite1_name:
                        satellites_to_check[name] = self.satellites[name]
            
            print(f"🔬 Advanced collision analysis for {len(satellites_to_check)} satellites...")
            print("   📊 Calculating orbital perturbations...")
            print("   🎯 Evaluating statistical probabilities...")
            
            # Analyze every 12 hours (more detailed)
            for hours in range(0, days_ahead * 24, 12):
                t = self.ts.tt_jd(self.ts.now().tt + hours / 24)
                
                # Position and velocity of satellite 1 with perturbations
                pos1_raw = sat1.at(t)
                
                # Add realistic perturbations
                perturbations1 = self.realistic_propagator.calculate_perturbations(pos1_raw, t)
                drag1 = self.realistic_propagator.atmospheric_drag(pos1_raw, t)
                
                # Calculate altitude for uncertainty model
                altitude1 = np.linalg.norm(pos1_raw.position.km) - 6371
                
                for sat2_name, sat2_data in satellites_to_check.items():
                    sat2 = sat2_data['satellite']
                    pos2_raw = sat2.at(t)
                    
                    # Perturbations for satellite 2
                    perturbations2 = self.realistic_propagator.calculate_perturbations(pos2_raw, t)
                    drag2 = self.realistic_propagator.atmospheric_drag(pos2_raw, t)
                    
                    altitude2 = np.linalg.norm(pos2_raw.position.km) - 6371
                    
                    # Calculate basic distance
                    distance_km = np.linalg.norm(
                        np.array(pos1_raw.position.km) - np.array(pos2_raw.position.km)
                    )
                    
                    if distance_km < threshold_km:
                        # Prepare data for probabilistic analysis
                        sat1_data_analysis = {
                            'position': pos1_raw.position.km,
                            'velocity': pos1_raw.velocity.km_per_s,
                            'altitude': altitude1,
                            'radius': 5.0,  # meters (estimation)
                            'perturbations': perturbations1 + drag1
                        }
                        
                        sat2_data_analysis = {
                            'position': pos2_raw.position.km,
                            'velocity': pos2_raw.velocity.km_per_s,
                            'altitude': altitude2,
                            'radius': 5.0,  # meters (estimation)
                            'perturbations': perturbations2 + drag2
                        }
                        
                        # Calculate advanced collision probability
                        collision_prob = self.advanced_collision_analyzer.calculate_collision_probability(
                            sat1_data_analysis, sat2_data_analysis, time_window_hours=24
                        )
                        
                        # Propagate uncertainty
                        orbital_period1 = 2 * np.pi * np.sqrt(
                            (np.linalg.norm(pos1_raw.position.km) * 1000)**3 / 
                            (3.986004418e14)  # GM de la Tierra
                        ) / 3600  # convertir a horas
                        
                        uncertainty1 = self.uncertainty_model.propagate_uncertainty(
                            hours, orbital_period1, 'moderate'
                        )
                        
                        detailed_analysis.append({
                            'datetime': t.utc_datetime(),
                            'satellite2': sat2_name,
                            'distance_km': distance_km,
                            'collision_probability': collision_prob.get('probability', 0),
                            'miss_distance_km': collision_prob.get('miss_distance_km', distance_km),
                            'combined_radius_km': collision_prob.get('combined_radius_km', 0.01),
                            'risk_level': collision_prob.get('risk_level', 'LOW'),
                            'uncertainty_ellipsoid': collision_prob.get('uncertainty_ellipsoid'),
                            'position_uncertainty_km': uncertainty1.get('total_position_uncertainty_km', 0),
                            'perturbations_applied': True,
                            'hours_from_now': hours,
                            'sat1_altitude_km': altitude1,
                            'sat2_altitude_km': altitude2
                        })
            
            # Advanced statistics
            if detailed_analysis:
                # Most critical encounter
                max_prob_encounter = max(detailed_analysis, key=lambda x: x['collision_probability'])
                min_distance_encounter = min(detailed_analysis, key=lambda x: x['distance_km'])
                
                # Global risk level
                max_probability = max(enc['collision_probability'] for enc in detailed_analysis)
                min_distance = min(enc['distance_km'] for enc in detailed_analysis)
                
                if max_probability > 1e-4 or min_distance < 1.0:
                    global_risk = 'CRITICAL'
                elif max_probability > 1e-6 or min_distance < 5.0:
                    global_risk = 'HIGH'
                elif max_probability > 1e-8 or min_distance < 10.0:
                    global_risk = 'MODERATE'
                else:
                    global_risk = 'LOW'
            else:
                max_prob_encounter = None
                min_distance_encounter = None
                global_risk = 'LOW'
                max_probability = 0
                min_distance = float('inf')
            
            return {
                'satellite': satellite1_name,
                'analysis_type': 'ADVANCED_PROBABILISTIC',
                'analysis_period_days': days_ahead,
                'threshold_km': threshold_km,
                'detailed_encounters': detailed_analysis,
                'total_encounters': len(detailed_analysis),
                'global_risk_level': global_risk,
                'max_collision_probability': max_probability,
                'min_distance_km': min_distance,
                'most_critical_encounter': max_prob_encounter,
                'closest_encounter': min_distance_encounter,
                'satellites_analyzed': len(satellites_to_check),
                'perturbations_included': ['J2', 'atmospheric_drag'],
                'uncertainty_modeling': True,
                'statistical_analysis': True
            }
            
        except Exception as e:
            return {
                'error': f'Error in advanced analysis: {str(e)}',
                'satellite': satellite1_name
            }
    
    def calculate_maneuver_time(self, v_rel: float, R_req: float = 1000.0, 
                              sigma_0: float = 100.0, k: float = 0.001, n: float = 3.0) -> Dict:
        """
        Calculate the time needed to start collision avoidance maneuvers
        
        Based on the equation: t ≥ (R_req + n·σ₀) / (v_rel − n·k)
        
        Args:
            v_rel: Relative velocity between objects (m/s)
                  In LEO: ~100 m/s up to ~14,000 m/s (head-on encounters)
            R_req: Desired safety distance (m). Ex: 100-1000 m
            sigma_0: Current positional uncertainty (1-sigma, m)
            k: Uncertainty growth rate (m/s)
            n: Confidence factor (ex: 3 for 3σ)
            
        Returns:
            Dict: Maneuver time analysis
        """
        try:
            # Validate input parameters
            if v_rel <= 0:
                return {'error': 'Relative velocity must be positive'}
            
            if R_req <= 0:
                return {'error': 'Safety distance must be positive'}
            
            if sigma_0 < 0:
                return {'error': 'Positional uncertainty cannot be negative'}
            
            # Calculate equation components
            numerator = R_req + n * sigma_0
            denominator = v_rel - n * k
            
            # Verify that the denominator is positive
            if denominator <= 0:
                return {
                    'error': 'Invalid configuration',
                    'reason': 'Relative velocity is insufficient compared to uncertainty growth',
                    'recommendation': 'Reduce confidence factor (n) or improve orbital precision (reduce k)',
                    'v_rel': v_rel,
                    'n_k': n * k,
                    'deficit': abs(denominator)
                }
            
            # Calculate maneuver time
            t_maneuver_seconds = numerator / denominator
            
            # Convert to different units
            t_minutes = t_maneuver_seconds / 60
            t_hours = t_minutes / 60
            t_days = t_hours / 24
            
            # Determine criticality based on available time
            if t_hours < 1:
                criticality = "🔴 CRITICAL"
                recommendation = "Immediate maneuver required"
            elif t_hours < 6:
                criticality = "🟠 HIGH"
                recommendation = "Prepare maneuver within the next few hours"
            elif t_hours < 24:
                criticality = "🟡 MEDIUM"
                recommendation = "Plan maneuver for today"
            elif t_days < 7:
                criticality = "🟢 LOW"
                recommendation = "Maneuver can be planned in advance"
            else:
                criticality = "🔵 MINIMAL"
                recommendation = "Sufficient time for detailed analysis"
            
            # Calculate alternative scenarios
            scenarios = []
            
            # Conservative scenario (n=2)
            if n != 2:
                t_conservative = (R_req + 2 * sigma_0) / (v_rel - 2 * k) if (v_rel - 2 * k) > 0 else None
                if t_conservative:
                    scenarios.append({
                        'name': 'Conservative (2σ)',
                        'nombre': 'Conservador (2σ)',
                        'time_seconds': t_conservative,
                        'time_hours': t_conservative / 3600,
                        'tiempo_horas': t_conservative / 3600
                    })
            
            # Aggressive scenario (n=1)
            if n != 1:
                t_aggressive = (R_req + 1 * sigma_0) / (v_rel - 1 * k) if (v_rel - 1 * k) > 0 else None
                if t_aggressive:
                    scenarios.append({
                        'name': 'Aggressive (1σ)',
                        'nombre': 'Agresivo (1σ)',
                        'time_seconds': t_aggressive,
                        'time_hours': t_aggressive / 3600,
                        'tiempo_horas': t_aggressive / 3600
                    })
            
            # Sensitivity analysis
            sensitivity = {
                'v_rel_impact': {
                    'description': 'Effect of ±10% in relative velocity',
                    'v_rel_high': v_rel * 1.1,
                    't_high': (numerator) / (v_rel * 1.1 - n * k) if (v_rel * 1.1 - n * k) > 0 else None,
                    'v_rel_low': v_rel * 0.9,
                    't_low': (numerator) / (v_rel * 0.9 - n * k) if (v_rel * 0.9 - n * k) > 0 else None
                },
                'uncertainty_impact': {
                    'description': 'Effect of ±50% in uncertainty',
                    'sigma_high': sigma_0 * 1.5,
                    't_sigma_high': (R_req + n * sigma_0 * 1.5) / denominator,
                    'sigma_low': sigma_0 * 0.5,
                    't_sigma_low': (R_req + n * sigma_0 * 0.5) / denominator
                }
            }
            
            return {
                'parameters': {
                    'v_rel_ms': v_rel,
                    'R_req_m': R_req,
                    'sigma_0_m': sigma_0,
                    'k_ms': k,
                    'confidence_factor': n
                },
                'maneuver_time': {
                    'seconds': t_maneuver_seconds,
                    'minutes': t_minutes,
                    'hours': t_hours,
                    'days': t_days,
                    'segundos': t_maneuver_seconds,
                    'minutos': t_minutes,
                    'horas': t_hours,
                    'dias': t_days
                },
                'tiempo_maniobra': {
                    'seconds': t_maneuver_seconds,
                    'minutes': t_minutes,
                    'hours': t_hours,
                    'days': t_days,
                    'segundos': t_maneuver_seconds,
                    'minutos': t_minutes,
                    'horas': t_hours,
                    'dias': t_days
                },
                'evaluation': {
                    'criticality': criticality,
                    'recommendation': recommendation
                },
                'evaluacion': {
                    'criticidad': criticality,
                    'recomendacion': recommendation
                },
                'calculation_components': {
                    'numerator': numerator,
                    'denominator': denominator,
                    'safety_margin': denominator - n * k
                },
                'alternative_scenarios': scenarios,
                'escenarios_alternativos': scenarios,
                'sensitivity_analysis': sensitivity,
                'interpretation': {
                    'leo_context': self._get_leo_context(v_rel),
                    'operational_recommendations': self._get_operational_recommendations(t_hours, v_rel)
                },
                'interpretacion': {
                    'contexto_leo': self._get_leo_context(v_rel),
                    'recomendaciones_operacionales': self._get_operational_recommendations(t_hours, v_rel)
                }
            }
            
        except Exception as e:
            return {'error': f'Error in calculation: {str(e)}'}
    
    def _get_leo_context(self, v_rel: float) -> Dict:
        """Provide specific context for LEO orbits"""
        if v_rel < 500:
            encounter_type = "Co-orbital or gentle encounter"
            description = "Satellites in similar orbits with low relative velocity"
        elif v_rel < 2000:
            encounter_type = "Lateral encounter"
            description = "Orbit crossing with moderate angle"
        elif v_rel < 8000:
            encounter_type = "Perpendicular encounter"
            description = "Orbits with different orbital planes"
        else:
            encounter_type = "Head-on encounter"
            description = "Orbits with opposite inclinations - maximum risk"
            
        return {
            'encounter_type': encounter_type,
            'tipo_encuentro': encounter_type,
            'description': description,
            'descripcion': description,
            'relative_velocity_ms': v_rel,
            'relative_velocity_kmh': v_rel * 3.6
        }
    
    def _get_operational_recommendations(self, t_hours: float, v_rel: float) -> List[str]:
        """Generate specific operational recommendations"""
        recommendations = []
        
        if t_hours < 1:
            recommendations.extend([
                "🚨 Activate emergency protocol",
                "📡 Contact control center immediately",
                "⚡ Execute pre-programmed emergency maneuver",
                "📊 Continuous telemetry monitoring"
            ])
        elif t_hours < 6:
            recommendations.extend([
                "📋 Prepare detailed maneuver plan",
                "🔍 Refine orbital data with additional measurements",
                "👥 Notify other satellite operators",
                "⚙️ Verify propulsion systems"
            ])
        elif t_hours < 24:
            recommendations.extend([
                "📈 Perform detailed conjunction analysis",
                "🛰️ Consider coordinated maneuvers if applicable",
                "📡 Increase tracking frequency",
                "💾 Document procedures for similar cases"
            ])
        else:
            recommendations.extend([
                "🔬 Exhaustive analysis of multiple scenarios",
                "🤝 Coordination with space agencies",
                "📊 Fuel optimization for maneuver",
                "🎯 Precision maneuver planning"
            ])
            
        # Specific recommendations by relative velocity
        if v_rel > 10000:
            recommendations.append("⚠️ High-velocity encounter - consider early maneuver")
        elif v_rel < 500:
            recommendations.append("🔄 Slow encounter - long-duration maneuver possible")
            
        return recommendations
    
    def plot_orbit(self, satellite_name: str, hours: int = 24) -> bool:
        """
        Visualize satellite orbit
        
        Args:
            satellite_name: Name of the satellite
            hours: Hours of orbit to show
            
        Returns:
            bool: True if plot was successful
        """
        if satellite_name not in self.satellites:
            print(f"❌ Satellite {satellite_name} not found")
            return False
            
        satellite = self.satellites[satellite_name]['satellite']
        
        # Calculate positions for visualization
        positions = []
        times = []
        
        start_time = self.ts.now()
        for minutes in range(0, hours * 60, 10):  # Every 10 minutes
            t = self.ts.tt_jd(start_time.tt + minutes / (24 * 60))
            geocentric = satellite.at(t)
            subpoint = geocentric.subpoint()
            
            positions.append([
                subpoint.longitude.degrees,
                subpoint.latitude.degrees
            ])
            times.append(t.utc_datetime())
        
        positions = np.array(positions)
        
        # Create the plot
        plt.figure(figsize=(15, 8))
        
        # Subplot 1: Trajectory on world map
        plt.subplot(1, 2, 1)
        plt.plot(positions[:, 0], positions[:, 1], 'b-', linewidth=2, alpha=0.7)
        plt.scatter(positions[0, 0], positions[0, 1], color='green', s=100, 
                   label='Start', zorder=5)
        plt.scatter(positions[-1, 0], positions[-1, 1], color='red', s=100, 
                   label='End', zorder=5)
        
        plt.xlim(-180, 180)
        plt.ylim(-90, 90)
        plt.xlabel('Longitude (°)')
        plt.ylabel('Latitude (°)')
        plt.title(f'Orbital Trajectory: {satellite_name}\n({hours} hours)')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Add reference lines
        plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
        plt.axvline(x=0, color='k', linestyle='--', alpha=0.3)
        
        # Subplot 2: Altitude vs time
        plt.subplot(1, 2, 2)
        altitudes = []
        for minutes in range(0, hours * 60, 10):
            t = self.ts.tt_jd(start_time.tt + minutes / (24 * 60))
            geocentric = satellite.at(t)
            subpoint = geocentric.subpoint()
            altitudes.append(subpoint.elevation.km)
        
        time_hours = [i/6 for i in range(len(altitudes))]  # Every 10 min = 1/6 hour
        plt.plot(time_hours, altitudes, 'r-', linewidth=2)
        plt.xlabel('Time (hours)')
        plt.ylabel('Altitude (km)')
        plt.title('Altitude Variation')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save the plot
        filename = f"orbit_{satellite_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"📊 Graph saved as: {filename}")
        
        plt.show()
        return True
    
    def plot_3d_earth_with_satellites(self, satellite_names: List[str], hours: int = 24) -> bool:
        """
        3D visualization of Earth with satellite trajectories
        
        Args:
            satellite_names: List of satellite names to visualize
            hours: Hours of orbit to show
            
        Returns:
            bool: True if visualization was successful
        """
        if not satellite_names:
            print("❌ No satellite names provided")
            return False
        
        # Verify that satellites exist
        valid_satellites = []
        for name in satellite_names:
            if name in self.satellites:
                valid_satellites.append(name)
            else:
                print(f"⚠️  Satellite {name} not found")
        
        if not valid_satellites:
            print("❌ No valid satellites found")
            return False
        
        print(f"🌍 Generating 3D visualization for {len(valid_satellites)} satellite(s)...")
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Add Earth as a sphere
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, np.pi, 50)
        x_earth = 6371 * np.outer(np.cos(u), np.sin(v))  # Earth radius: 6371 km
        y_earth = 6371 * np.outer(np.sin(u), np.sin(v))
        z_earth = 6371 * np.outer(np.ones(np.size(u)), np.cos(v))
        
        fig.add_trace(go.Surface(
            x=x_earth, y=y_earth, z=z_earth,
            colorscale='Blues',
            opacity=0.7,
            name='Earth',
            showscale=False,
            hovertemplate='Earth<extra></extra>'
        ))
        
        # Colors for different satellites
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'yellow', 'pink', 'cyan']
        
        # Add satellite trajectories
        for i, satellite_name in enumerate(valid_satellites):
            satellite = self.satellites[satellite_name]['satellite']
            color = colors[i % len(colors)]
            
            # Calculate satellite positions
            positions_3d = []
            times = []
            
            start_time = self.ts.now()
            for minutes in range(0, hours * 60, 15):  # Every 15 minutes for better performance
                t = self.ts.tt_jd(start_time.tt + minutes / (24 * 60))
                geocentric = satellite.at(t)
                
                # Convert to Cartesian coordinates (km)
                position = geocentric.position.km
                positions_3d.append(position)
                times.append(t.utc_datetime())
            
            positions_3d = np.array(positions_3d)
            
            # Add satellite trajectory
            fig.add_trace(go.Scatter3d(
                x=positions_3d[:, 0],
                y=positions_3d[:, 1], 
                z=positions_3d[:, 2],
                mode='lines+markers',
                line=dict(color=color, width=4),
                marker=dict(size=3, color=color),
                name=f'{satellite_name}',
                hovertemplate=f'<b>{satellite_name}</b><br>' +
                            'X: %{x:.1f} km<br>' +
                            'Y: %{y:.1f} km<br>' +
                            'Z: %{z:.1f} km<extra></extra>'
            ))
            
            # Mark initial and final positions
            fig.add_trace(go.Scatter3d(
                x=[positions_3d[0, 0]],
                y=[positions_3d[0, 1]],
                z=[positions_3d[0, 2]],
                mode='markers',
                marker=dict(size=8, color='lightgreen', symbol='diamond'),
                name=f'{satellite_name} - Start',
                showlegend=False,
                hovertemplate=f'<b>{satellite_name} - Start</b><br>' +
                            'X: %{x:.1f} km<br>' +
                            'Y: %{y:.1f} km<br>' +
                            'Z: %{z:.1f} km<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter3d(
                x=[positions_3d[-1, 0]],
                y=[positions_3d[-1, 1]],
                z=[positions_3d[-1, 2]],
                mode='markers',
                marker=dict(size=8, color='darkred', symbol='cross'),
                name=f'{satellite_name} - End',
                showlegend=False,
                hovertemplate=f'<b>{satellite_name} - End</b><br>' +
                            'X: %{x:.1f} km<br>' +
                            'Y: %{y:.1f} km<br>' +
                            'Z: %{z:.1f} km<extra></extra>'
            ))
        
        # Configure the layout
        fig.update_layout(
            title=f'🛰️ 3D Visualization: Satellites around Earth<br>' +
                  f'<sub>Trajectories of {hours} hours - {len(valid_satellites)} satellite(s)</sub>',
            scene=dict(
                xaxis_title='X (km)',
                yaxis_title='Y (km)',
                zaxis_title='Z (km)',
                aspectmode='cube',
                camera=dict(
                    eye=dict(x=2, y=2, z=2)
                ),
                bgcolor='black'
            ),
            font=dict(size=12),
            width=1000,
            height=800,
            margin=dict(l=0, r=0, t=50, b=0)
        )
        
        # Show the visualization
        fig.show()
        
        # Save as interactive HTML
        filename = f"satellite_3d_visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        fig.write_html(filename)
        print(f"🌍 3D visualization saved as: {filename}")
        
        return True
    
    def comprehensive_collision_analysis(self, satellite1_name: str, satellite2_name: str = None,
                                       threshold_km: float = 10.0, days_ahead: int = 7) -> Dict:
        """
        Complete collision analysis including maneuver time calculation
        
        Args:
            satellite1_name: First satellite to analyze
            satellite2_name: Second satellite (if None, analyzes against sample)
            threshold_km: Minimum distance to consider risk (km)
            days_ahead: Days to analyze ahead
            
        Returns:
            Dict: Complete collision analysis and maneuver time
        """
        print(f"🔍 Starting complete collision analysis for {satellite1_name}...")
        
        # Perform basic collision analysis
        collision_analysis = self.analyze_collision_risk(
            satellite1_name, satellite2_name, threshold_km, days_ahead
        )
        
        if 'error' in collision_analysis:
            return collision_analysis
        
        # If there are close encounters, calculate maneuver parameters
        maneuver_analyses = []
        
        if collision_analysis['close_encounters']:
            print(f"⚠️  {len(collision_analysis['close_encounters'])} close encounters detected")
            
            for encounter in collision_analysis['close_encounters'][:5]:  # Analyze first 5
                # Calculate estimated relative velocity for encounter
                sat1_pos = np.array(encounter['satellite1_pos'])
                sat2_pos = np.array(encounter['satellite2_pos'])
                distance_km = encounter['distance_km']
                
                # Estimate relative velocity based on typical LEO orbit
                # For LEO satellites: orbital velocity ~7.8 km/s
                orbital_velocity = 7800  # m/s
                
                # Estimate relative velocity based on encounter type
                if distance_km < 1:
                    # Very close encounter, probably head-on
                    v_rel_estimate = orbital_velocity * 1.8  # ~14,000 m/s
                elif distance_km < 5:
                    # Close encounter, moderate angle  
                    v_rel_estimate = orbital_velocity * 1.2  # ~9,400 m/s
                else:
                    # Distant encounter, parallel
                    v_rel_estimate = orbital_velocity * 0.2  # ~1,560 m/s
                
                # Typical parameters for analysis
                params_scenarios = [
                    {
                        'name': 'Conservative',
                        'R_req': 1000,  # 1 km safety margin
                        'sigma_0': 200,  # 200 m uncertainty
                        'k': 0.002,     # Moderate growth
                        'n': 3          # 3 sigma
                    },
                    {
                        'name': 'Standard',
                        'R_req': 500,   # 500 m safety margin
                        'sigma_0': 100,  # 100 m uncertainty
                        'k': 0.001,     # Normal growth
                        'n': 2.5        # 2.5 sigma
                    },
                    {
                        'name': 'Aggressive',
                        'R_req': 200,   # 200 m safety margin
                        'sigma_0': 50,   # 50 m uncertainty
                        'k': 0.0005,    # Low growth
                        'n': 2          # 2 sigma
                    }
                ]
                
                encounter_maneuvers = []
                
                for scenario in params_scenarios:
                    maneuver_calc = self.calculate_maneuver_time(
                        v_rel=v_rel_estimate,
                        R_req=scenario['R_req'],
                        sigma_0=scenario['sigma_0'],
                        k=scenario['k'],
                        n=scenario['n']
                    )
                    
                    if 'error' not in maneuver_calc:
                        encounter_maneuvers.append({
                            'scenario': scenario['name'],
                            'parameters': scenario,
                            'maneuver_time': maneuver_calc['tiempo_maniobra'],
                            'criticality': maneuver_calc['evaluacion']['criticidad'],
                            'recommendation': maneuver_calc['evaluacion']['recomendacion']
                        })
                
                maneuver_analyses.append({
                    'encounter': {
                        'date': encounter['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC'),
                        'satellite_2': encounter['satellite2'],
                        'distance_km': distance_km,
                        'estimated_relative_velocity': v_rel_estimate
                    },
                    'maneuver_analysis': encounter_maneuvers
                })
        
        # Generate general recommendations
        general_recommendations = self._generate_general_recommendations(
            collision_analysis, maneuver_analyses
        )
        
        # Calculate time to first encounter
        first_encounter_time = None
        if collision_analysis['close_encounters']:
            first_encounter = min(collision_analysis['close_encounters'], 
                                 key=lambda x: x['datetime'])
            first_encounter_time = {
                'date': first_encounter['datetime'],
                'hours_remaining': (first_encounter['datetime'] - datetime.now()).total_seconds() / 3600,
                'distance_km': first_encounter['distance_km']
            }
        
        return {
            'collision_analysis': collision_analysis,
            'maneuver_analyses': maneuver_analyses,
            'first_encounter_time': first_encounter_time,
            'general_recommendations': general_recommendations,
            'executive_summary': self._generate_executive_summary(
                collision_analysis, maneuver_analyses, first_encounter_time
            )
        }
    
    def _generate_general_recommendations(self, collision_analysis: Dict, 
                                        maneuver_analyses: List[Dict]) -> List[str]:
        """Generate general recommendations based on analysis"""
        recommendations = []
        
        risk_level = collision_analysis.get('risk_level', 'LOW')
        total_encounters = collision_analysis.get('total_encounters', 0)
        
        if risk_level == 'CRITICAL':
            recommendations.extend([
                "🚨 CRITICAL ALERT: Implement emergency protocol immediately",
                "📡 Establish continuous communication with control centers",
                "⚡ Prepare automatic emergency maneuver",
                "🎯 Consider multiple maneuver options"
            ])
        elif risk_level == 'HIGH':
            recommendations.extend([
                "⚠️ HIGH RISK: Plan maneuver within next 24 hours",
                "📊 Refine orbital data with additional tracking",
                "🤝 Coordinate with other operators if necessary",
                "📋 Prepare contingency plan"
            ])
        elif risk_level == 'MEDIUM':
            recommendations.extend([
                "🟡 MEDIUM RISK: Increased monitoring required",
                "📈 Detailed conjunction analysis",
                "🔍 Evaluation of maneuver options",
                "📅 Preventive planning"
            ])
        
        if total_encounters > 3:
            recommendations.append(f"📊 Multiple encounters ({total_encounters}) - consider major orbital change")
        
        if maneuver_analyses:
            min_time = min([
                min([m['maneuver_time']['horas'] for m in analysis['maneuver_analysis']])
                for analysis in maneuver_analyses if analysis['maneuver_analysis']
            ], default=float('inf'))
            
            if min_time < 1:
                recommendations.append("⏰ Maneuver time < 1 hour - Immediate action required")
            elif min_time < 6:
                recommendations.append("⏰ Maneuver time < 6 hours - Urgent preparation")
        
        return recommendations
    
    def _generate_executive_summary(self, collision_analysis: Dict, 
                                  maneuver_analyses: List[Dict], 
                                  first_encounter: Dict) -> Dict:
        """Generate executive summary of analysis"""
        
        summary = {
            'satellite': collision_analysis.get('satellite', 'Unknown'),
            'risk_level': collision_analysis.get('risk_level', 'LOW'),
            'total_encounters': collision_analysis.get('total_encounters', 0),
            'analysis_period_days': collision_analysis.get('analysis_period_days', 0)
        }
        
        if first_encounter:
            summary['first_encounter'] = {
                'time_hours': first_encounter['hours_remaining'],
                'distance_km': first_encounter['distance_km'],
                'date': first_encounter['date'].strftime('%Y-%m-%d %H:%M UTC')
            }
        
        if maneuver_analyses:
            # Minimum maneuver time among all scenarios
            maneuver_times = []
            for analysis in maneuver_analyses:
                for maneuver in analysis['maneuver_analysis']:
                    maneuver_times.append(maneuver['maneuver_time']['horas'])
            
            if maneuver_times:
                summary['maneuver_time'] = {
                    'minimum_hours': min(maneuver_times),
                    'maximum_hours': max(maneuver_times),
                    'average_hours': sum(maneuver_times) / len(maneuver_times)
                }
        
        # Determine recommended action
        if summary['risk_level'] == 'CRITICAL':
            summary['recommended_action'] = "IMMEDIATE MANEUVER"
        elif summary['risk_level'] == 'HIGH':
            summary['recommended_action'] = "PREPARE URGENT MANEUVER"
        elif summary['risk_level'] == 'MEDIUM':
            summary['recommended_action'] = "INCREASED MONITORING"
        else:
            summary['recommended_action'] = "ROUTINE TRACKING"
        
        return summary
    
    def find_collision_cases(self, threshold_km: float = 50.0, days_ahead: int = 7, 
                           max_satellites: int = 500) -> List[Dict]:
        """
        Search for real collision cases between satellites
        Specific function to find real close encounters
        
        Args:
            threshold_km: Maximum distance to consider close encounter
            days_ahead: Days to analyze
            max_satellites: Maximum number of satellites to analyze
            
        Returns:
            List[Dict]: List of collision cases found
        """
        print(f"🔍 EXHAUSTIVE SEARCH FOR COLLISION CASES")
        print(f"📊 Analyzing up to {max_satellites} satellites...")
        print(f"📏 Threshold: {threshold_km} km | 📅 Period: {days_ahead} days")
        print("-" * 60)
        
        collision_cases = []
        satellites_list = list(self.satellites.keys())
        
        # Analyze a larger sample of satellites
        sample_size = min(max_satellites, len(satellites_list))
        sample_satellites = satellites_list[:sample_size]
        
        analyzed_pairs = set()  # Avoid analyzing the same pair twice
        
        for i, sat1_name in enumerate(sample_satellites):
            if i % 50 == 0:  # Show progress every 50 satellites
                progress = (i / sample_size) * 100
                print(f"📈 Progress: {progress:.1f}% ({i}/{sample_size}) - Cases found: {len(collision_cases)}")
            
            try:
                sat1 = self.satellites[sat1_name]['satellite']
                
                # Analyze against a subsample of other satellites
                for j, sat2_name in enumerate(sample_satellites[i+1:i+51], i+1):  # Next 50
                    if j >= len(sample_satellites):
                        break
                        
                    pair = tuple(sorted([sat1_name, sat2_name]))
                    if pair in analyzed_pairs:
                        continue
                    analyzed_pairs.add(pair)
                    
                    try:
                        sat2 = self.satellites[sat2_name]['satellite']
                        
                        # Check encounters every 2 hours for greater precision
                        for hours in range(0, days_ahead * 24, 2):
                            t = self.ts.tt_jd(self.ts.now().tt + hours / 24)
                            
                            pos1 = sat1.at(t)
                            pos2 = sat2.at(t)
                            
                            # Calculate distance
                            distance_km = np.linalg.norm(
                                np.array(pos1.position.km) - np.array(pos2.position.km)
                            )
                            
                            if distance_km < threshold_km:
                                # We found a collision case!
                                collision_cases.append({
                                    'satellite1': sat1_name,
                                    'satellite2': sat2_name,
                                    'datetime': t.utc_datetime(),
                                    'distance_km': distance_km,
                                    'hours_from_now': hours,
                                    'satellite1_pos': pos1.position.km,
                                    'satellite2_pos': pos2.position.km,
                                    'relative_velocity_estimated': self._estimate_relative_velocity(
                                        pos1.position.km, pos2.position.km, distance_km
                                    )
                                })
                                
                                print(f"🚨 CASE FOUND: {sat1_name} vs {sat2_name}")
                                print(f"   📅 {t.utc_datetime().strftime('%Y-%m-%d %H:%M')} UTC")
                                print(f"   📏 Distance: {distance_km:.2f} km")
                                
                                # If we find several cases, we don't need more
                                if len(collision_cases) >= 5:
                                    print(f"✅ Sufficient cases found. Stopping search.")
                                    return collision_cases
                                    
                    except Exception as e:
                        continue  # Continue with next satellite
                        
            except Exception as e:
                continue  # Continue with next main satellite
        
        print(f"✅ Search completed. Cases found: {len(collision_cases)}")
        return collision_cases
    
    def _estimate_relative_velocity(self, pos1: np.ndarray, pos2: np.ndarray, 
                                  distance_km: float) -> float:
        """Estimate relative velocity based on positions and distance"""
        # Typical orbital speed in LEO
        orbital_speed = 7800  # m/s
        
        # Estimate based on encounter distance
        if distance_km < 5:
            return orbital_speed * 1.8  # Probable head-on encounter
        elif distance_km < 20:
            return orbital_speed * 1.2  # Angular encounter
        else:
            return orbital_speed * 0.5  # Lateral encounter
    
    def demonstrate_collision_case(self) -> None:
        """
        Demonstrate a found collision case with complete analysis
        """
        print("🔍 REAL COLLISION CASE DEMONSTRATION")
        print("=" * 60)
        
        # Search for collision cases
        cases = self.find_collision_cases(threshold_km=100, days_ahead=3, max_satellites=200)
        
        if not cases:
            print("❌ No collision cases found in analyzed sample")
            print("💡 This can happen because:")
            print("   • Satellites are well separated")
            print("   • Analyzed sample is small")
            print("   • Thresholds are very strict")
            print("\n🎭 Generating simulated case for demonstration...")
            
            # Create a simulated case based on real data
            self._create_simulated_case()
            return
        
        # Analyze first case found
        case = cases[0]
        print(f"\n🚨 COLLISION CASE DETECTED:")
        print(f"🛰️  Satellite 1: {case['satellite1']}")
        print(f"🛰️  Satellite 2: {case['satellite2']}")
        print(f"📅 Date/Time: {case['datetime'].strftime('%Y-%m-%d %H:%M')} UTC")
        print(f"📏 Distance: {case['distance_km']:.2f} km")
        print(f"⏰ In: {case['hours_from_now']} hours")
        
        # Calculate maneuver time for this case
        v_rel = case['relative_velocity_estimated']
        print(f"\n⚡ MANEUVER TIME ANALYSIS:")
        print(f"🚀 Estimated relative velocity: {v_rel:.0f} m/s")
        
        # Various maneuver scenarios
        scenarios = [
            {'name': 'Conservative', 'R_req': 2000, 'sigma_0': 200, 'k': 0.002, 'n': 3},
            {'name': 'Standard', 'R_req': 1000, 'sigma_0': 100, 'k': 0.001, 'n': 2.5},
            {'name': 'Aggressive', 'R_req': 500, 'sigma_0': 50, 'k': 0.0008, 'n': 2}
        ]
        
        print(f"\n📊 MANEUVER SCENARIOS:")
        for scenario in scenarios:
            result = self.calculate_maneuver_time(
                v_rel=v_rel,
                R_req=scenario['R_req'],
                sigma_0=scenario['sigma_0'],
                k=scenario['k'],
                n=scenario['n']
            )
            
            if 'error' not in result:
                tiempo = result['tiempo_maniobra']
                print(f"   • {scenario['name']}: {tiempo['horas']:.2f} hours")
                print(f"     {result['evaluacion']['criticidad']}")
            else:
                print(f"   • {scenario['name']}: {result['error']}")
        
        # Show all cases found
        if len(cases) > 1:
            print(f"\n📋 OTHER CASES DETECTED:")
            for i, other_case in enumerate(cases[1:], 2):
                print(f"   {i}. {other_case['satellite1']} vs {other_case['satellite2']}")
                print(f"      📅 {other_case['datetime'].strftime('%Y-%m-%d %H:%M')} UTC")
                print(f"      📏 {other_case['distance_km']:.2f} km")
    
    def _create_simulated_case(self) -> None:
        """Create a simulated case based on real satellites"""
        print("🎭 SIMULATED DEMONSTRATION CASE:")
        print("=" * 50)
        
        # Use real satellites to create credible scenario
        satellite_names = list(self.satellites.keys())
        sat1 = satellite_names[10] if len(satellite_names) > 10 else satellite_names[0]
        sat2 = satellite_names[50] if len(satellite_names) > 50 else satellite_names[1]
        
        import datetime
        future_time = datetime.datetime.now() + datetime.timedelta(hours=28, minutes=45)
        
        print(f"🛰️  Satellite 1: {sat1}")
        print(f"🛰️  Satellite 2: {sat2}")
        print(f"📅 Projected encounter: {future_time.strftime('%Y-%m-%d %H:%M')} UTC")
        print(f"📏 Estimated minimum distance: 15.3 km")
        print(f"🚀 Relative velocity: 8,200 m/s")
        print(f"⏰ Time to encounter: 28.75 hours")
        
        print(f"\n⚡ MANEUVER TIME ANALYSIS:")
        result = self.calculate_maneuver_time(
            v_rel=8200,
            R_req=1000,
            sigma_0=120,
            k=0.001,
            n=3
        )
        
        if 'error' not in result:
            tiempo = result['tiempo_maniobra']
            print(f"⏰ Required maneuver time: {tiempo['horas']:.2f} hours")
            print(f"{result['evaluacion']['criticidad']}")
            print(f"💡 {result['evaluacion']['recomendacion']}")
            
            print(f"\n📊 EVALUATION:")
            available_time = 28.75
            required_time = tiempo['horas']
            
            if available_time > required_time:
                margin = available_time - required_time
                print(f"✅ SAFE MARGIN: {margin:.1f} hours available")
                print(f"🎯 Execute maneuver before: {(future_time - datetime.timedelta(hours=required_time)).strftime('%Y-%m-%d %H:%M')} UTC")
            else:
                deficit = required_time - available_time
                print(f"🚨 CRITICAL SITUATION: Deficit of {deficit:.1f} hours")
                print(f"⚡ Immediate maneuver required")
        
        print(f"\n💡 This is an example of how the system would detect and analyze")
        print(f"   a real case of satellite conjunction.")


# NEW MODULE FOR HACKATHON - ISL CONTROL SYSTEM
class ISLControlSystem:
    """
    Inter-Satellite Link (ISL) Control System with propulsion awareness
    
    This module simulates the logic that would run on the IENAI chip to:
    - Manage satellite network traffic based on collision risk
    - Optimize routing considering propulsor state
    - Make autonomous maneuver and communication decisions
    """
    
    def __init__(self, analyzer: SatelliteAnalyzer):
        self.analyzer = analyzer
        self.network_nodes = []  # List of satellites in network
        self.current_routes = {}  # Current communication routes
        
    def determine_thrust_aware_routing(self, sat_local_name: str, sat_neighbor_name: str, 
                                       collision_risk_data: Dict, propellant_level: float) -> Dict:
        """
        Simulates routing logic based on collision risk and IENAI propulsor state.
        THIS FUNCTION WOULD RUN ON THE IENAI CHIP.
        
        Args:
            sat_local_name: Local satellite name (this satellite)
            sat_neighbor_name: Neighbor satellite in network
            collision_risk_data: Collision risk data
            propellant_level: Propellant level (0.0 to 1.0)
            
        Returns:
            Dict: ISL system commands and decisions
        """
        
        # 1. Evaluate if maneuver is needed (using existing logic)
        risk_level = collision_risk_data.get('risk_level', 'LOW')
        close_encounters = collision_risk_data.get('close_encounters', [])
        
        # 2. Calculate maneuver parameters based on risk
        maneuver_analysis = None
        time_to_maneuver_hours = float('inf')
        
        if risk_level in ['HIGH', 'CRITICAL'] and close_encounters:
            # Get closest encounter
            nearest_encounter = min(close_encounters, key=lambda x: x['distance_km'])
            
            # Estimate relative velocity based on encounter distance
            if nearest_encounter['distance_km'] < 5:
                v_rel_estimate = 12000  # Critical head-on encounter
            elif nearest_encounter['distance_km'] < 20:
                v_rel_estimate = 8000   # Perpendicular encounter
            else:
                v_rel_estimate = 3000   # Lateral encounter
            
            # Calculate required maneuver time
            maneuver_analysis = self.analyzer.calculate_maneuver_time(
                v_rel=v_rel_estimate,
                R_req=500.0,     # 500m safety for commercial satellites
                sigma_0=100.0,   # 100m standard uncertainty
                k=0.001,         # Normal uncertainty growth
                n=3.0            # 3 sigma confidence
            )
            
            if 'error' not in maneuver_analysis:
                time_to_maneuver_hours = maneuver_analysis['tiempo_maniobra']['horas']
        
        # 3. ISL DECISION LOGIC (Heart of the project)
        decision_result = self._make_isl_decision(
            sat_local_name, sat_neighbor_name, risk_level, 
            time_to_maneuver_hours, propellant_level, maneuver_analysis
        )
        
        return decision_result
    
    def _make_isl_decision(self, sat_local: str, sat_neighbor: str, risk_level: str,
                          time_hours: float, propellant: float, maneuver_data: Dict) -> Dict:
        """
        Core ISL decision logic
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Classify temporal urgency
        if time_hours < 1:
            urgency = "CRITICAL_IMMEDIATE"
        elif time_hours < 6:
            urgency = "CRITICAL_SHORT_TERM"
        elif time_hours < 24:
            urgency = "MODERATE"
        else:
            urgency = "LOW"
        
        # MAIN DECISION TREE
        if urgency in ["CRITICAL_IMMEDIATE", "CRITICAL_SHORT_TERM"]:
            if propellant > 0.15:  # Sufficient fuel (>15%)
                command = "THRUST_IMMINENT"
                action = f"Preparing evasion maneuver. Diverting critical traffic to satellite {sat_neighbor}"
                network_priority = "HIGH_REROUTE"
                bandwidth_allocation = 0.2  # 20% bandwidth for maneuver coordination
                
            elif propellant > 0.05:  # Limited fuel (5-15%)
                command = "THRUST_CONDITIONAL"
                action = f"Conditional maneuver. Evaluating alternatives. Alerting {sat_neighbor}"
                network_priority = "MEDIUM_REROUTE"
                bandwidth_allocation = 0.1  # 10% for coordination
                
            else:  # Insufficient fuel (<5%)
                command = "THRUST_IMPOSSIBLE"
                action = f"Insufficient fuel. Issuing position alert. Total transfer to {sat_neighbor}"
                network_priority = "EMERGENCY_REROUTE"
                bandwidth_allocation = 0.05  # 5% minimum for alerts
                
        elif urgency == "MODERATE":
            if propellant > 0.25:  # Good fuel level
                command = "THRUST_PLANNED"
                action = f"Planned maneuver. Coordinating with {sat_neighbor} for traffic redistribution"
                network_priority = "PLANNED_REROUTE"
                bandwidth_allocation = 0.8  # 80% normal operation
                
            else:
                command = "THRUST_PRESERVE"
                action = f"Conserving fuel. Requesting network support from {sat_neighbor}"
                network_priority = "FUEL_CONSERVATION"
                bandwidth_allocation = 0.6  # 60% reduced operation
                
        else:  # LOW risk
            command = "ROUTE_NORMAL"
            action = "Normal operation. No imminent collision threat"
            network_priority = "NORMAL"
            bandwidth_allocation = 1.0  # 100% normal operation
        
        # Generate ISL communication protocol
        isl_protocol = self._generate_isl_protocol(
            command, sat_local, sat_neighbor, urgency, propellant
        )
        
        return {
            'timestamp': timestamp,
            'command': command,
            'action': action,
            'urgency_level': urgency,
            'risk_assessment': risk_level,
            'propellant_status': f"{propellant*100:.1f}%",
            'time_to_maneuver_hours': time_hours,
            'network_priority': network_priority,
            'bandwidth_allocation': bandwidth_allocation,
            'target_satellite': sat_neighbor,
            'isl_protocol': isl_protocol,
            'maneuver_data': maneuver_data,
            'autonomous_decision': True,
            'chip_location': 'IENAI_PROCESSOR'
        }
    
    def _generate_isl_protocol(self, command: str, sat_local: str, sat_neighbor: str,
                              urgency: str, propellant: float) -> Dict:
        """
        Generate communication protocol between satellites
        """
        protocol = {
            'message_type': 'ISL_COORDINATION',
            'source': sat_local,
            'destination': sat_neighbor,
            'priority': 'HIGH' if urgency.startswith('CRITICAL') else 'MEDIUM',
            'encryption': 'AES256_QUANTUM_SAFE',
            'compression': 'SATELLITE_OPTIMIZED'
        }
        
        if command == "THRUST_IMMINENT":
            protocol['payload'] = {
                'alert_type': 'IMMINENT_MANEUVER',
                'maneuver_window': '< 1 hour',
                'requested_action': 'TAKE_TRAFFIC_LOAD',
                'backup_required': True,
                'telemetry_sharing': True
            }
        elif command == "THRUST_IMPOSSIBLE":
            protocol['payload'] = {
                'alert_type': 'PROPULSION_FAILURE',
                'maneuver_capability': False,
                'requested_action': 'EMERGENCY_BACKUP',
                'position_alert': True,
                'ground_notification': True
            }
        elif command == "ROUTE_NORMAL":
            protocol['payload'] = {
                'alert_type': 'STATUS_NORMAL',
                'maneuver_capability': True,
                'requested_action': 'MAINTAIN_NORMAL_OPS',
                'health_check': True
            }
        else:
            protocol['payload'] = {
                'alert_type': 'CONDITIONAL_MANEUVER',
                'maneuver_probability': f"{min(1.0, (1.0 - propellant) + 0.5):.2f}",
                'requested_action': 'STANDBY_SUPPORT',
                'monitoring_required': True
            }
        
        return protocol
    
    def simulate_constellation_response(self, decision_result: Dict, 
                                      constellation_size: int = 5) -> Dict:
        """
        Simulate constellation response to ISL command
        """
        constellation_response = {
            'constellation_id': 'IENAI_NETWORK_ALPHA',
            'total_satellites': constellation_size,
            'responding_satellites': [],
            'network_adaptation': {},
            'collective_decision': None
        }
        
        # Simulate response from other satellites
        for i in range(constellation_size):
            sat_id = f"IENAI_SAT_{i+1:02d}"
            if sat_id != decision_result.get('target_satellite', ''):
                
                # Simulate capacity of each satellite
                sat_capacity = np.random.uniform(0.6, 1.0)  # 60-100% capacity
                sat_fuel = np.random.uniform(0.1, 0.9)      # 10-90% fuel
                
                response = {
                    'satellite_id': sat_id,
                    'available_capacity': f"{sat_capacity*100:.1f}%",
                    'fuel_level': f"{sat_fuel*100:.1f}%",
                    'can_assist': sat_capacity > 0.3,
                    'priority_level': 'HIGH' if sat_capacity > 0.7 else 'MEDIUM'
                }
                
                constellation_response['responding_satellites'].append(response)
        
        # Calculate network adaptation
        total_capacity = sum([float(sat['available_capacity'].rstrip('%'))/100 
                            for sat in constellation_response['responding_satellites']])
        
        constellation_response['network_adaptation'] = {
            'total_available_capacity': f"{total_capacity*100:.1f}%",
            'load_distribution': 'AUTOMATIC',
            'failover_ready': total_capacity > 1.5,
            'latency_impact': 'MINIMAL' if total_capacity > 2.0 else 'MODERATE'
        }
        
        # Collective constellation decision
        if decision_result['urgency_level'].startswith('CRITICAL'):
            constellation_response['collective_decision'] = 'EMERGENCY_PROTOCOL_ACTIVATED'
        elif total_capacity > 1.8:
            constellation_response['collective_decision'] = 'FULL_SUPPORT_GRANTED'
        else:
            constellation_response['collective_decision'] = 'LIMITED_SUPPORT_AVAILABLE'
        
        return constellation_response


class HackathonDemo:
    """
    Class to demonstrate ISL system in hackathon
    """
    
    def __init__(self, analyzer: SatelliteAnalyzer):
        self.analyzer = analyzer
        self.isl_system = ISLControlSystem(analyzer)
        
    def run_complete_demo(self):
        """
        Run complete ISL system demonstration for hackathon
        """
        print("🚀 COMPLETE ISL-IENAI SYSTEM DEMONSTRATION")
        print("=" * 70)
        print("🎯 Inter-Satellite Link Control System with Propulsion Awareness")
        print("💡 Simulating autonomous operation on IENAI chip")
        print("-" * 70)
        
        # Test scenarios
        scenarios = [
            {
                'name': '🔴 CRITICAL SCENARIO: Imminent Head-On Encounter',
                'risk_data': {
                    'risk_level': 'CRITICAL',
                    'close_encounters': [{'distance_km': 2.5, 'datetime': datetime.now()}]
                },
                'propellant': 0.85,  # 85% fuel
                'description': 'Satellite with good fuel detects imminent collision'
            },
            {
                'name': '🟠 CRITICAL SCENARIO: Low Fuel',
                'risk_data': {
                    'risk_level': 'HIGH',
                    'close_encounters': [{'distance_km': 8.3, 'datetime': datetime.now()}]
                },
                'propellant': 0.03,  # 3% fuel
                'description': 'Satellite with critical fuel detects threat'
            },
            {
                'name': '🟡 MODERATE SCENARIO: Planned Encounter',
                'risk_data': {
                    'risk_level': 'MEDIUM',
                    'close_encounters': [{'distance_km': 25.7, 'datetime': datetime.now()}]
                },
                'propellant': 0.60,  # 60% fuel
                'description': 'Encounter detected with time to plan'
            },
            {
                'name': '🟢 NORMAL SCENARIO: Routine Operation',
                'risk_data': {
                    'risk_level': 'LOW',
                    'close_encounters': []
                },
                'propellant': 0.75,  # 75% fuel
                'description': 'Normal operation with no threats detected'
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{i}. {scenario['name']}")
            print(f"   📝 {scenario['description']}")
            print(f"   ⛽ Fuel: {scenario['propellant']*100:.1f}%")
            
            # Execute ISL analysis
            decision = self.isl_system.determine_thrust_aware_routing(
                sat_local_name="IENAI_SAT_01",
                sat_neighbor_name="IENAI_SAT_02", 
                collision_risk_data=scenario['risk_data'],
                propellant_level=scenario['propellant']
            )
            
            # Show results
            print(f"   🤖 AUTONOMOUS DECISION: {decision['command']}")
            print(f"   ⚡ Action: {decision['action']}")
            print(f"   📡 Network priority: {decision['network_priority']}")
            print(f"   📊 Bandwidth: {decision['bandwidth_allocation']*100:.0f}%")
            
            if decision['time_to_maneuver_hours'] < float('inf'):
                print(f"   ⏰ Time to maneuver: {decision['time_to_maneuver_hours']:.2f} hours")
            
            # Simulate constellation response
            constellation_response = self.isl_system.simulate_constellation_response(decision)
            print(f"   🛰️  Constellation response: {constellation_response['collective_decision']}")
            print(f"   🌐 Available capacity: {constellation_response['network_adaptation']['total_available_capacity']}")
            
            print("   " + "-" * 50)
        
        print(f"\n✅ DEMONSTRATION COMPLETED")
        print(f"🎯 The ISL-IENAI system is ready for:")
        print(f"   • Autonomous collision risk detection")
        print(f"   • Decision making based on propulsion state")
        print(f"   • Intelligent satellite network management")
        print(f"   • Real-time constellation coordination")
        print(f"   • Completely autonomous operation in space")
    
    
    def plot_orbital_animation(self, satellite_name: str, hours: int = 24, frames: int = 100) -> bool:
        """
        Create an animation of satellite orbit around Earth
        
        Args:
            satellite_name: Satellite name
            hours: Orbit hours to animate
            frames: Number of frames in animation
            
        Returns:
            bool: True if animation was successful
        """
        try:
            if satellite_name not in self.satellites:
                print(f"❌ Satellite {satellite_name} not found")
                return False
            
            satellite = self.satellites[satellite_name]['satellite']
            print(f"🎬 Generating orbital animation for {satellite_name}...")
            print(f"⏱️  Calculating {frames} positions for {hours} hours...")
            
            # Calculate all positions
            all_positions = []
            start_time = self.ts.now()
            
            for frame in range(frames + 1):
                minutes = (hours * 60 * frame) / frames
                t = self.ts.tt_jd(start_time.tt + minutes / (24 * 60))
                geocentric = satellite.at(t)
                position = geocentric.position.km
                all_positions.append(position)
            
            all_positions = np.array(all_positions)
            print(f"✅ Positions calculated")
            
            # Create animation
            fig = go.Figure()
            
            # Add Earth with simpler colorscale
            u = np.linspace(0, 2 * np.pi, 30)
            v = np.linspace(0, np.pi, 30)
            x_earth = 6371 * np.outer(np.cos(u), np.sin(v))
            y_earth = 6371 * np.outer(np.sin(u), np.sin(v))
            z_earth = 6371 * np.outer(np.ones(np.size(u)), np.cos(v))
            
            fig.add_trace(go.Surface(
                x=x_earth, y=y_earth, z=z_earth,
                colorscale='Blues',  # Cambié de 'Earth' a 'Blues' para mayor compatibilidad
                opacity=0.8,
                name='Tierra',
                showscale=False,
                hovertemplate='Tierra<extra></extra>'
            ))
            
            print(f"🌍 Tierra agregada a la visualización")
            
            # Crear frames para la animación (reducir cantidad para mejor rendimiento)
            frames_list = []
            step = max(1, frames // 20)  # Máximo 20 frames para mejor rendimiento
            
            for i in range(0, frames + 1, step):
                if i >= len(all_positions):
                    break
                    
                frame_data = [
                    go.Surface(
                        x=x_earth, y=y_earth, z=z_earth,
                        colorscale='Blues',
                        opacity=0.8,
                        showscale=False,
                        hovertemplate='Tierra<extra></extra>'
                    ),
                    go.Scatter3d(
                        x=all_positions[:i+1, 0],
                        y=all_positions[:i+1, 1],
                        z=all_positions[:i+1, 2],
                        mode='lines',
                        line=dict(color='red', width=6),
                        name='Trayectoria',
                        hovertemplate='Trayectoria<extra></extra>'
                    ),
                    go.Scatter3d(
                        x=[all_positions[i, 0]],
                        y=[all_positions[i, 1]],
                        z=[all_positions[i, 2]],
                        mode='markers',
                        marker=dict(size=12, color='yellow', symbol='circle'),
                        name='Satellite',
                        hovertemplate=f'{satellite_name}<br>X: %{{x:.1f}} km<br>Y: %{{y:.1f}} km<br>Z: %{{z:.1f}} km<extra></extra>'
                    )
                ]
                frames_list.append(go.Frame(data=frame_data, name=str(i)))
            
            fig.frames = frames_list
            print(f"🎞️  {len(frames_list)} frames de animación creados")
            
            # Configurar la animación con controles mejorados
            fig.update_layout(
                title=f'🎬 Animación Orbital: {satellite_name}<br><sub>Período: {hours} horas | Frames: {len(frames_list)}</sub>',
                scene=dict(
                    xaxis_title='X (km)',
                    yaxis_title='Y (km)', 
                    zaxis_title='Z (km)',
                    aspectmode='cube',
                    camera=dict(eye=dict(x=2.5, y=2.5, z=2.5)),
                    bgcolor='black'
                ),
                font=dict(size=12),
                width=1000,
                height=700,
                updatemenus=[{
                    'type': 'buttons',
                    'showactive': False,
                    'x': 0.1,
                    'y': 0.02,
                    'buttons': [
                        {
                            'label': '▶️ Reproducir',
                            'method': 'animate',
                            'args': [None, {
                                'frame': {'duration': 200, 'redraw': True},
                                'fromcurrent': True,
                                'transition': {'duration': 100}
                            }]
                        },
                        {
                            'label': '⏸️ Pausar',
                            'method': 'animate',
                            'args': [[None], {
                                'frame': {'duration': 0, 'redraw': False},
                                'mode': 'immediate',
                                'transition': {'duration': 0}
                            }]
                        },
                        {
                            'label': '🔄 Reiniciar',
                            'method': 'animate',
                            'args': [None, {
                                'frame': {'duration': 200, 'redraw': True},
                                'mode': 'immediate',
                                'transition': {'duration': 0}
                            }]
                        }
                    ]
                }],
                sliders=[{
                    'active': 0,
                    'yanchor': 'top',
                    'xanchor': 'left',
                    'currentvalue': {
                        'font': {'size': 20},
                        'prefix': 'Frame:',
                        'visible': True,
                        'xanchor': 'right'
                    },
                    'transition': {'duration': 100, 'easing': 'cubic-in-out'},
                    'pad': {'b': 10, 't': 50},
                    'len': 0.9,
                    'x': 0.1,
                    'y': 0,
                    'steps': [
                        {
                            'args': [[f.name], {
                                'frame': {'duration': 100, 'redraw': True},
                                'mode': 'immediate',
                                'transition': {'duration': 100}
                            }],
                            'label': f.name,
                            'method': 'animate'
                        } for f in frames_list
                    ]
                }]
            )
            
            print(f"🎨 Animation configuration completed")
            
            # Show the visualization
            print(f"🌐 Opening animation in browser...")
            fig.show()
            
            # Save as HTML
            safe_name = satellite_name.replace(' ', '_').replace('(', '').replace(')', '')
            filename = f"orbital_animation_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            fig.write_html(filename)
            print(f"💾 Animation saved as: {filename}")
            print(f"📁 Location: {os.path.abspath(filename)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating animation: {str(e)}")
            print(f"💡 Suggestions:")
            print(f"   1. Verify that the satellite name is correct")
            print(f"   2. Try with fewer frames (e.g.: 20-30)")
            print(f"   3. Reduce the hours (e.g.: 2-6 hours)")
            return False


def show_menu():
    """Show options menu"""
    print("\n" + "=" * 60)
    print("🎯 AVAILABLE OPTIONS:")
    print("   1. Search satellite (intelligent search)")
    print("   2. View popular satellites by category")
    print("   3. Detailed information of a satellite")
    print("   4. Calculate future orbits")
    print("   5. Analyze collision risk")
    print("   6. Visualize orbit (2D)")
    print("   7. 3D Visualization (Earth + Satellites)")
    print("   8. 3D Orbital Animation")
    print("   9. Export complete satellite list")
    print("  10. Calculate evasion maneuver time")
    print("  11. Complete collision + maneuver analysis")
    print("  12. 🔍 SEARCH REAL COLLISION CASES")
    print("  13. 🚀 ISL-IENAI SYSTEM DEMO (HACKATHON)")
    print("  14. 🤖 Individual ISL Simulator")
    print("  15. 🧪 ADVANCED COLLISION ANALYSIS (J2 + Probability)")
    print("  16. Exit")
    print("=" * 60)


def main():
    """Main program function"""
    print("=" * 60)
    print("🛰️  SATELLITE ANALYSIS SYSTEM")
    print("    NASA Space App Challenge 2025 - Malkie Space")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = SatelliteAnalyzer()
    
    # Download satellite data
    if not analyzer.download_tle_data():
        print("❌ Error downloading data. Terminating program.")
        return
    
    print("\n✅ System loaded successfully!")
    
    # Menu will be shown automatically in each loop iteration
    
    while True:
        try:
            # Show menu in each iteration
            show_menu()
            print("\n" + "-" * 40)
            option = input("Select an option (1-16): ").strip()
            
            if option == '1':
                # Intelligent satellite search
                search_term = input("🔍 Enter satellite name to search: ").strip()
                if search_term:
                    results = analyzer.smart_search(search_term)
                    
                    if results['total_found'] > 0:
                        print(f"\n✅ Found {results['total_found']} satellites:")
                        
                        # Show exact matches first
                        if results['exact_matches']:
                            print("\n🎯 EXACT MATCHES:")
                            for i, name in enumerate(results['exact_matches'], 1):
                                print(f"   {i}. {name}")
                        
                        # Show partial matches by category
                        if results['category_matches']:
                            print("\n📊 RESULTS BY CATEGORY:")
                            for category, satellites in results['category_matches'].items():
                                print(f"\n   📂 {category.capitalize()}:")
                                for i, name in enumerate(satellites[:5], 1):  # Maximum 5 per category
                                    print(f"      {i}. {name}")
                                if len(satellites) > 5:
                                    print(f"      ... and {len(satellites) - 5} more in this category")
                        
                        # Show suggestions if few matches
                        if results['suggestions'] and results['total_found'] < 5:
                            print(f"\n💡 RELATED SUGGESTIONS:")
                            for i, suggestion in enumerate(results['suggestions'][:8], 1):
                                print(f"   {i}. {suggestion}")
                    else:
                        print("❌ No satellites found with that name")
                        
                        # Show popular examples
                        print("\n🌟 Maybe you were looking for one of these popular satellites?")
                        analyzer.show_satellite_examples()
                        
            elif option == '2':
                # View popular satellites by category
                print("🌟 Popular satellites by category:")
                popular = analyzer.get_popular_satellites()
                for category, satellites in popular.items():
                    print(f"\n📂 {category.upper()}:")
                    for i, name in enumerate(satellites, 1):
                        print(f"   {i}. {name}")
                        
            elif option == '3':
                # Detailed satellite information
                sat_name = input("📋 Satellite name: ").strip()
                if sat_name:
                    info = analyzer.get_satellite_info(sat_name)
                    if 'error' not in info:
                        print(f"\n🛰️  DETAILED INFORMATION: {sat_name}")
                        print("=" * 50)
                        print(f"📅 Data date: {info['current_time']}")
                        print(f"📍 Current position:")
                        print(f"   • Latitude: {info['position']['latitude']:.3f}°")
                        print(f"   • Longitude: {info['position']['longitude']:.3f}°")
                        print(f"   • Altitude: {info['position']['altitude']:.1f} km")
                        print(f"📊 Orbital parameters:")
                        print(f"   • Inclination: {info['orbital_elements'].get('inclination', 'N/A')}")
                        print(f"   • Eccentricity: {info['orbital_elements'].get('eccentricity', 'N/A')}")
                        print(f"   • Period: {info['orbital_elements'].get('period_minutes', 'N/A')} min")
                    else:
                        print(f"❌ {info['error']}")
                        
            elif option == '4':
                # Calculate future orbits
                sat_name = input("🚀 Satellite name: ").strip()
                if sat_name:
                    try:
                        days = int(input("📅 Days to calculate (default 7): ") or "7")
                        days = min(days, 180)  # Limit to maximum 180 days
                        print(f"⏳ Calculating future positions for {days} days...")
                        positions = analyzer.calculate_future_positions(sat_name, days)
                        
                        if positions:
                            print(f"\n🛰️  ORBITAL PREDICTIONS: {sat_name}")
                            print("=" * 60)
                            for pos in positions[:20]:  # Show first 20
                                print(f"📅 {pos['datetime'].strftime('%Y-%m-%d %H:%M')} UTC")
                                print(f"   Lat: {pos['latitude']:7.3f}°  Lon: {pos['longitude']:8.3f}°  Alt: {pos['altitude_km']:7.1f} km")
                            
                            if len(positions) > 20:
                                print(f"   ... and {len(positions) - 20} more predictions")
                                
                            # Show statistics
                            altitudes = [pos['altitude_km'] for pos in positions]
                            print(f"\n📈 STATISTICS:")
                            print(f"   • Minimum altitude: {min(altitudes):.1f} km")
                            print(f"   • Maximum altitude: {max(altitudes):.1f} km")
                            print(f"   • Average altitude: {sum(altitudes)/len(altitudes):.1f} km")
                        else:
                            print("❌ Could not calculate positions")
                            print("💡 Suggestions:")
                            print("   • Verify satellite name is exact")
                            print("   • Use option 1 to search available satellites")
                            print("   • Try popular names like: ISS (ZARYA), STARLINK-1007")
                    except ValueError:
                        print("❌ Invalid number of days. Must be an integer.")
                        
            elif option == '5':
                # Analyze collision risk
                sat_name = input("⚠️  Main satellite: ").strip()
                if sat_name:
                    sat2_name = input("🎯 Second satellite (Enter to analyze against all): ").strip() or None
                    try:
                        threshold = float(input("📏 Minimum distance in km (default 10): ") or "10")
                        days = int(input("📅 Days to analyze (4): ") or "4")
                        
                        print("⏳ Analyzing collision risk...")
                        risk_analysis = analyzer.analyze_collision_risk(sat_name, sat2_name, threshold, days)
                        
                        if 'error' not in risk_analysis:
                            print(f"\n⚠️  COLLISION RISK ANALYSIS")
                            print("=" * 50)
                            print(f"🛰️  Satellite: {risk_analysis['satellite']}")
                            print(f"📊 Risk level: {risk_analysis['risk_level']}")
                            print(f"📈 Close encounters: {risk_analysis['total_encounters']}")
                            print(f"📅 Analysis period: {risk_analysis['analysis_period_days']} days")
                            print(f"📏 Threshold: {risk_analysis['threshold_km']} km")
                            
                            if risk_analysis['close_encounters']:
                                print(f"\n🚨 CLOSE ENCOUNTERS DETECTED:")
                                for enc in risk_analysis['close_encounters'][:10]:  # First 10
                                    print(f"  • {enc['datetime'].strftime('%Y-%m-%d %H:%M')} UTC")
                                    print(f"    With: {enc['satellite2']}")
                                    print(f"    Distance: {enc['distance_km']:.2f} km")
                            else:
                                print("✅ No close encounters detected")
                        else:
                            print(f"❌ {risk_analysis['error']}")
                    except ValueError:
                        print("❌ Invalid values")
                        
            elif option == '6':
                # Visualize 2D orbit
                sat_name = input("📈 Satellite name: ").strip()
                if sat_name:
                    try:
                        hours = int(input("⏰ Orbit hours to show (default 24): ") or "24")
                        print("⏳ Generating 2D visualization...")
                        analyzer.plot_orbit(sat_name, hours)
                    except ValueError:
                        print("❌ Invalid number of hours")
                        
            elif option == '7':
                # 3D visualization of Earth with satellites
                print("🌍 3D visualization of satellites around Earth")
                satellites_input = input("🛰️  Satellite names (comma separated): ").strip()
                if satellites_input:
                    satellite_names = [name.strip() for name in satellites_input.split(',')]
                    try:
                        hours = int(input("⏰ Trajectory hours (default 12): ") or "12")
                        print("⏳ Generating 3D visualization...")
                        analyzer.plot_3d_earth_with_satellites(satellite_names, hours)
                    except ValueError:
                        print("❌ Invalid number of hours")
                        
            elif option == '8':
                # 3D orbital animation
                sat_name = input("🎬 Satellite name to animate: ").strip()
                if sat_name:
                    try:
                        hours = int(input("⏰ Orbit hours to animate (default 6): ") or "6")
                        frames = int(input("🎞️  Number of frames (default 50): ") or "50")
                        print("⏳ Generating 3D animation...")
                        analyzer.plot_orbital_animation(sat_name, hours, frames)
                    except ValueError:
                        print("❌ Invalid values")
                        
            elif option == '9':
                # Export complete satellite list
                filename = input("📁 File name (default: available_satellites.txt): ").strip() or "available_satellites.txt"
                print("⏳ Exporting satellite list...")
                if analyzer.export_satellites_list(filename):
                    print(f"✅ List exported successfully to: {filename}")
                else:
                    print("❌ Error exporting list")
                    
            elif option == '10':
                # Calculate evasion maneuver time
                print("⏰ EVASION MANEUVER TIME CALCULATION")
                print("=" * 50)
                try:
                    v_rel = float(input("🚀 Relative velocity (m/s) [100-14000]: "))
                    R_req = float(input("📏 Safety distance (m) [default 1000]: ") or "1000")
                    sigma_0 = float(input("📊 Positional uncertainty (m) [default 100]: ") or "100")
                    k = float(input("📈 Uncertainty growth rate (m/s) [default 0.001]: ") or "0.001")
                    n = float(input("🎯 Confidence factor (sigma) [default 3]: ") or "3")
                    
                    result = analyzer.calculate_maneuver_time(v_rel, R_req, sigma_0, k, n)
                    
                    if 'error' not in result:
                        print(f"\n⏰ MANEUVER ANALYSIS RESULT")
                        print("=" * 50)
                        print(f"⚡ Required maneuver time:")
                        
                        # Use maneuver_time (with fallback to tiempo_maniobra)
                        tiempo_data = result.get('maneuver_time') or result.get('tiempo_maniobra', {})
                        if tiempo_data:
                            print(f"   • {tiempo_data.get('segundos', tiempo_data.get('seconds', 0)):.1f} seconds")
                            print(f"   • {tiempo_data.get('minutos', tiempo_data.get('minutes', 0)):.1f} minutes")
                            print(f"   • {tiempo_data.get('horas', tiempo_data.get('hours', 0)):.2f} hours")
                            print(f"   • {tiempo_data.get('dias', tiempo_data.get('days', 0)):.3f} days")
                        
                        # Use evaluation (with fallback to evaluacion)
                        eval_data = result.get('evaluation') or result.get('evaluacion', {})
                        if eval_data:
                            criticality = eval_data.get('criticality') or eval_data.get('criticidad', 'UNKNOWN')
                            recommendation = eval_data.get('recommendation') or eval_data.get('recomendacion', 'No recommendation')
                            print(f"\n{criticality}")
                            print(f"💡 {recommendation}")
                        
                        # Use interpretation (with fallback to interpretacion)
                        interp_data = result.get('interpretation') or result.get('interpretacion', {})
                        if interp_data:
                            leo_context = interp_data.get('leo_context') or interp_data.get('contexto_leo', {})
                            if leo_context:
                                encounter_type = leo_context.get('encounter_type') or leo_context.get('tipo_encuentro', 'Unknown')
                                description = leo_context.get('description') or leo_context.get('descripcion', 'No description')
                                print(f"\n🎯 Encounter context:")
                                print(f"   • {encounter_type}")
                                print(f"   • {description}")
                            
                            # Operational recommendations
                            op_recs = interp_data.get('operational_recommendations') or interp_data.get('recomendaciones_operacionales', [])
                            if op_recs:
                                print(f"\n📋 Operational recommendations:")
                                for rec in op_recs:
                                    print(f"   {rec}")
                        
                        # Use alternative_scenarios (with fallback to escenarios_alternativos)
                        scenarios = result.get('alternative_scenarios') or result.get('escenarios_alternativos', [])
                        if scenarios:
                            print(f"\n📊 Alternative scenarios:")
                            for scenario in scenarios:
                                if isinstance(scenario, dict):
                                    name = scenario.get('name') or scenario.get('nombre', 'Unknown scenario')
                                    hours = scenario.get('time_hours') or scenario.get('tiempo_horas', 0)
                                    print(f"   • {name}: {hours:.2f} hours")
                    else:
                        print(f"❌ {result['error']}")
                        if 'recommendation' in result:
                            print(f"💡 {result['recommendation']}")
                            
                except ValueError:
                    print("❌ Invalid values. Make sure to enter valid numbers.")
                    
            elif option == '11':
                # Complete collision + maneuver analysis
                print("🔍 COMPLETE ANALYSIS: COLLISION + MANEUVER")
                print("=" * 50)
                sat_name = input("🛰️  Main satellite name: ").strip()
                if sat_name:
                    sat2_name = input("🎯 Second satellite (Enter to analyze sample): ").strip() or None
                    try:
                        threshold = float(input("📏 Minimum distance in km (default 10): ") or "10")
                        days = int(input("📅 Days to analyze (default 7): ") or "7")
                        
                        print("⏳ Performing complete analysis...")
                        comprehensive = analyzer.comprehensive_collision_analysis(
                            sat_name, sat2_name, threshold, days
                        )
                        
                        if 'error' not in comprehensive:
                            # Show executive summary
                            summary = comprehensive['executive_summary']
                            print(f"\n📊 EXECUTIVE SUMMARY")
                            print("=" * 40)
                            print(f"🛰️  Satellite: {summary['satellite']}")
                            print(f"⚠️  Risk level: {summary['risk_level']}")
                            print(f"📈 Total encounters: {summary['total_encounters']}")
                            print(f"🎯 Recommended action: {summary['recommended_action']}")
                            
                            if summary.get('first_encounter'):
                                pe = summary['first_encounter']
                                print(f"\n⏰ FIRST ENCOUNTER:")
                                print(f"   • Date: {pe['date']}")
                                print(f"   • In: {pe['time_hours']:.1f} hours")
                                print(f"   • Distance: {pe['distance_km']:.2f} km")
                            
                            if summary.get('maneuver_time'):
                                tm = summary['maneuver_time']
                                print(f"\n⚡ MANEUVER TIME:")
                                print(f"   • Minimum: {tm['minimum_hours']:.2f} hours")
                                print(f"   • Maximum: {tm['maximum_hours']:.2f} hours")
                                print(f"   • Average: {tm['average_hours']:.2f} hours")
                            
                            # Show general recommendations
                            if comprehensive['general_recommendations']:
                                print(f"\n💡 GENERAL RECOMMENDATIONS:")
                                for rec in comprehensive['general_recommendations']:
                                    print(f"   {rec}")
                            
                            # Show detailed maneuver analysis if encounters exist
                            if comprehensive['maneuver_analyses']:
                                print(f"\n📊 DETAILED MANEUVER ANALYSIS:")
                                for i, analysis in enumerate(comprehensive['maneuver_analyses'][:3], 1):
                                    encounter = analysis['encounter']
                                    print(f"\n   {i}. Encounter: {encounter['date']}")
                                    print(f"      With: {encounter['satellite_2']}")
                                    print(f"      Distance: {encounter['distance_km']:.2f} km")
                                    print(f"      Estimated V_rel: {encounter['estimated_relative_velocity']:.0f} m/s")
                                    
                                    for maneuver in analysis['maneuver_analysis']:
                                        print(f"      • {maneuver['scenario']}: {maneuver['maneuver_time']['horas']:.2f} hours")
                                        print(f"        {maneuver['criticality']}")
                        else:
                            print(f"❌ {comprehensive['error']}")
                            
                    except ValueError:
                        print("❌ Invalid values")
                        
            elif option == '12':
                # Search for real collision cases
                print("🔍 EXHAUSTIVE SEARCH FOR COLLISION CASES")
                print("=" * 50)
                print("💡 This function will search for real close encounter cases")
                print("   between satellites in the current database.")
                print()
                
                try:
                    threshold = float(input("📏 Distance threshold in km (default 75): ") or "75")
                    days = int(input("📅 Days to analyze (default 3): ") or "3")
                    max_sats = int(input("🛰️  Maximum satellites to analyze (default 300): ") or "300")
                    
                    print("\n⏳ Starting exhaustive search...")
                    print("⚠️  This operation may take several minutes...")
                    
                    # Execute collision case search
                    analyzer.demonstrate_collision_case()
                    
                except ValueError:
                    print("❌ Invalid values")
                except KeyboardInterrupt:
                    print("\n⏹️  Search cancelled by user")
                    
            elif option == '13':
                # Complete ISL-IENAI system demo for hackathon
                print("🚀 STARTING ISL-IENAI SYSTEM DEMONSTRATION")
                print("=" * 60)
                print("💡 Inter-Satellite Link Control System")
                print("🎯 Demonstrating autonomous decision-making in space")
                print()
                
                try:
                    demo = HackathonDemo(analyzer)
                    demo.run_complete_demo()
                except Exception as e:
                    print(f"❌ Error in demonstration: {str(e)}")
                    
            elif option == '14':
                # Individual ISL simulator
                print("🤖 INDIVIDUAL ISL SIMULATOR")
                print("=" * 50)
                print("💡 Configure your own ISL analysis scenario")
                print()
                
                try:
                    sat_local = input("🛰️  Local satellite (default: IENAI_SAT_01): ").strip() or "IENAI_SAT_01"
                    sat_neighbor = input("📡 Neighbor satellite (default: IENAI_SAT_02): ").strip() or "IENAI_SAT_02"
                    
                    print("\n🎯 Configure risk scenario:")
                    print("   1. CRITICAL risk (encounter < 5 km)")
                    print("   2. HIGH risk (encounter 5-20 km)")
                    print("   3. MEDIUM risk (encounter 20-50 km)")
                    print("   4. LOW risk (no threats)")
                    
                    risk_choice = input("Select risk level (1-4): ").strip()
                    propellant = float(input("⛽ Fuel level (0.0-1.0): ") or "0.5")
                    
                    # Configure risk data according to selection
                    risk_configs = {
                        '1': {'risk_level': 'CRITICAL', 'close_encounters': [{'distance_km': 2.1, 'datetime': datetime.now()}]},
                        '2': {'risk_level': 'HIGH', 'close_encounters': [{'distance_km': 12.5, 'datetime': datetime.now()}]},
                        '3': {'risk_level': 'MEDIUM', 'close_encounters': [{'distance_km': 35.0, 'datetime': datetime.now()}]},
                        '4': {'risk_level': 'LOW', 'close_encounters': []}
                    }
                    
                    risk_data = risk_configs.get(risk_choice, risk_configs['4'])
                    
                    # Execute ISL analysis
                    isl_system = ISLControlSystem(analyzer)
                    result = isl_system.determine_thrust_aware_routing(
                        sat_local, sat_neighbor, risk_data, propellant
                    )
                    
                    # Show detailed results
                    print(f"\n🤖 ISL ANALYSIS RESULT:")
                    print("=" * 50)
                    print(f"⏰ Timestamp: {result['timestamp']}")
                    print(f"🚀 Command: {result['command']}")
                    print(f"⚡ Action: {result['action']}")
                    print(f"🎯 Urgency: {result['urgency_level']}")
                    print(f"📊 Risk: {result['risk_assessment']}")
                    print(f"⛽ Fuel: {result['propellant_status']}")
                    
                    if result['time_to_maneuver_hours'] < float('inf'):
                        print(f"⏰ Time to maneuver: {result['time_to_maneuver_hours']:.3f} hours")
                    
                    print(f"📡 Network priority: {result['network_priority']}")
                    print(f"📶 Bandwidth: {result['bandwidth_allocation']*100:.0f}%")
                    print(f"🎯 Target satellite: {result['target_satellite']}")
                    print(f"🧠 Autonomous decision: {result['autonomous_decision']}")
                    print(f"💻 Location: {result['chip_location']}")
                    
                    # Show ISL protocol
                    protocol = result['isl_protocol']
                    print(f"\n📡 ISL PROTOCOL:")
                    print(f"   • Type: {protocol['message_type']}")
                    print(f"   • Priority: {protocol['priority']}")
                    print(f"   • Encryption: {protocol['encryption']}")
                    print(f"   • Requested action: {protocol['payload']['requested_action']}")
                    
                    # Simulate constellation response
                    constellation = isl_system.simulate_constellation_response(result)
                    print(f"\n🌐 CONSTELLATION RESPONSE:")
                    print(f"   • Collective decision: {constellation['collective_decision']}")
                    print(f"   • Total capacity: {constellation['network_adaptation']['total_available_capacity']}")
                    print(f"   • Responding satellites: {len(constellation['responding_satellites'])}")
                    print(f"   • Failover ready: {constellation['network_adaptation']['failover_ready']}")
                    
                except ValueError:
                    print("❌ Invalid values")
                except Exception as e:
                    print(f"❌ Error in simulation: {str(e)}")
                        
            elif option == '15':
                # ADVANCED COLLISION ANALYSIS
                print("🧪 ADVANCED COLLISION ANALYSIS")
                print("=" * 50)
                print("Includes:")
                print("  • J2 perturbations (Earth's oblateness)")
                print("  • Atmospheric drag")
                print("  • Uncertainty ellipsoids")
                print("  • Real statistical probability")
                print("  • Non-linear uncertainty propagation")
                
                sat_name = input("\n🛰️ Main satellite name: ").strip()
                if not sat_name:
                    print("❌ Satellite name required")
                    continue
                
                sat2_name = input("🛰️ Second satellite name (Enter for multiple analysis): ").strip()
                if not sat2_name:
                    sat2_name = None
                
                try:
                    threshold = float(input("📏 Distance threshold in km (default 10): ") or "10")
                    days = int(input("📅 Days to analyze (default 3): ") or "3")
                    
                    print(f"\n🔬 Starting advanced analysis...")
                    print("⚠️ This may take several minutes due to complex calculations...")
                    
                    result = analyzer.advanced_collision_analysis(
                        sat_name, sat2_name, threshold, days
                    )
                    
                    if 'error' in result:
                        print(f"❌ {result['error']}")
                    else:
                        print(f"\n🎯 ADVANCED ANALYSIS COMPLETED")
                        print("=" * 50)
                        print(f"🛰️ Satellite: {result['satellite']}")
                        print(f"🔬 Analysis type: {result['analysis_type']}")
                        print(f"🎯 Global risk level: {result['global_risk_level']}")
                        print(f"📊 Maximum collision probability: {result['max_collision_probability']:.2e}")
                        print(f"📏 Minimum distance: {result['min_distance_km']:.3f} km")
                        print(f"🔍 Encounters detected: {result['total_encounters']}")
                        print(f"🛰️ Satellites analyzed: {result['satellites_analyzed']}")
                        
                        print(f"\n✅ Advanced features applied:")
                        for perturbation in result['perturbations_included']:
                            print(f"   • {perturbation}")
                        print(f"   • Uncertainty modeling: {'✅' if result['uncertainty_modeling'] else '❌'}")
                        print(f"   • Statistical analysis: {'✅' if result['statistical_analysis'] else '❌'}")
                        
                        if result['most_critical_encounter']:
                            critical = result['most_critical_encounter']
                            print(f"\n🚨 MOST CRITICAL ENCOUNTER:")
                            print(f"   📅 Date: {critical['datetime']}")
                            print(f"   🛰️ Satellite: {critical['satellite2']}")
                            print(f"   📊 Probability: {critical['collision_probability']:.2e}")
                            print(f"   📏 Distance: {critical['distance_km']:.3f} km")
                            print(f"   ⚠️ Risk level: {critical['risk_level']}")
                            print(f"   📊 Positional uncertainty: {critical['position_uncertainty_km']:.3f} km")
                        
                        if result['detailed_encounters']:
                            print(f"\n📋 ENCOUNTER SUMMARY:")
                            for i, enc in enumerate(result['detailed_encounters'][:5], 1):
                                print(f"   {i}. {enc['satellite2']} - "
                                      f"Prob: {enc['collision_probability']:.2e}, "
                                      f"Dist: {enc['distance_km']:.3f} km, "
                                      f"Risk: {enc['risk_level']}")
                            
                            if len(result['detailed_encounters']) > 5:
                                print(f"   ... and {len(result['detailed_encounters']) - 5} more encounters")
                        
                except ValueError:
                    print("❌ Invalid numeric values")
                except Exception as e:
                    print(f"❌ Error during analysis: {str(e)}")
                        
            elif option == '16':
                print("👋 Thank you for using the Satellite Analysis System!")
                break
                        
            elif option == '2':
                # View popular satellites by category
                print("🌟 POPULAR SATELLITES BY CATEGORY")
                print("=" * 50)
                
                popular = analyzer.get_popular_satellites()
                
                for category, satellites in popular.items():
                    if satellites:
                        print(f"\n📂 {category}:")
                        for i, sat in enumerate(satellites, 1):
                            print(f"   {i}. {sat}")
                    else:
                        print(f"\n📂 {category}: (No se encontraron en los datos actuales)")
                
                print(f"\n💡 TIP: Copy any exact name to use in other options")
                
            elif option == '3':
                # Detailed information
                sat_name = input("📡 Enter exact satellite name: ").strip()
                if not sat_name:
                    print("❌ Empty name")
                elif sat_name not in analyzer.satellites:
                    print(f"❌ Satellite '{sat_name}' not found")
                    # Offer suggestions
                    suggestions = analyzer.suggest_satellites(sat_name)
                    if suggestions:
                        print(f"\n🔍 ¿Quisiste decir alguno de estos?")
                        for i, suggestion in enumerate(suggestions[:5], 1):
                            print(f"   {i}. {suggestion}")
                else:
                    info = analyzer.get_satellite_info(sat_name)
                    if info:
                        print(f"\n📊 INFORMATION FOR {info['name']}")
                        print("-" * 50)
                        print(f"Category: {info['category']}")
                        print(f"Current position:")
                        print(f"  • Latitude: {info['current_position']['latitude']:.4f}°")
                        print(f"  • Longitude: {info['current_position']['longitude']:.4f}°")
                        print(f"  • Altitude: {info['current_position']['altitude_km']:.2f} km")
                        
                        print(f"\nOrbital elements:")
                        oe = info['orbital_elements']
                        print(f"  • Inclination: {oe['inclination_deg']:.2f}°")
                        print(f"  • Eccentricity: {oe['eccentricity']:.6f}")
                        print(f"  • Orbital period: {oe['period_hours']:.2f} hours")
                        print(f"  • Approx altitude: {oe['approx_altitude_km']:.0f} km")
                        print(f"  • Revolutions/day: {oe['mean_motion_rev_per_day']:.6f}")
                    else:
                        print("❌ Satellite not found")
                        
            elif option == '4':
                # Calculate future orbits
                sat_name = input("🚀 Satellite name: ").strip()
                if sat_name:
                    try:
                        days = int(input("📅 Days into the future (max 4): ") or "4")
                        days = min(days, 180)
                        
                        print(f"⏳ Calculating future positions for {days} days...")
                        positions = analyzer.calculate_future_positions(sat_name, days)
                        
                        if positions:
                            print(f"\n✅ Calculated {len(positions)} positions")
                            print("First 5 positions:")
                            for i, pos in enumerate(positions[:5]):
                                print(f"  {i+1}. {pos['datetime'].strftime('%Y-%m-%d %H:%M')} UTC")
                                print(f"     Lat: {pos['latitude']:.3f}°, Lon: {pos['longitude']:.3f}°")
                                print(f"     Alt: {pos['altitude_km']:.1f} km")
                        else:
                            print("❌ Could not calculate positions")
                    except ValueError:
                        print("❌ Invalid number of days")
                        
            elif option == '5':
                # Collision risk analysis
                sat_name = input("⚠️  Satellite name: ").strip()
                if sat_name:
                    try:
                        days = int(input("📅 Days to analyze (max 180): ") or "180")
                        days = min(days, 180)
                        threshold = float(input("🎯 Distancia umbral en km (default 10): ") or "10")
                        
                        print(f"⏳ Analyzing collision risk...")
                        risk_analysis = analyzer.analyze_collision_risk(sat_name, None, threshold, days)
                        
                        if 'error' not in risk_analysis:
                            print(f"\n🎯 COLLISION RISK ANALYSIS")
                            print("-" * 50)
                            print(f"Satellite: {risk_analysis['satellite']}")
                            print(f"Analysis period: {risk_analysis['analysis_period_days']} days")
                            print(f"Satellites analyzed: {risk_analysis['satellites_analyzed']}")
                            print(f"Distance threshold: {risk_analysis['threshold_km']} km")
                            print(f"RISK LEVEL: {risk_analysis['risk_level']}")
                            print(f"Close encounters: {risk_analysis['total_encounters']}")
                            
                            if risk_analysis['close_encounters']:
                                print("\n⚠️  CLOSE ENCOUNTERS DETECTED:")
                                for enc in risk_analysis['close_encounters'][:10]:  # First 10
                                    print(f"  • {enc['datetime'].strftime('%Y-%m-%d %H:%M')} UTC")
                                    print(f"    With: {enc['satellite2']}")
                                    print(f"    Distance: {enc['distance_km']:.2f} km")
                            else:
                                print("✅ No close encounters detected")
                        else:
                            print(f"❌ {risk_analysis['error']}")
                    except ValueError:
                        print("❌ Invalid values")
                        
            elif option == '6':
                # Visualize 2D orbit
                sat_name = input("📈 Satellite name: ").strip()
                if sat_name:
                    try:
                        hours = int(input("⏰ Orbit hours to display (default 24): ") or "24")
                        print("⏳ Generating 2D visualization...")
                        analyzer.plot_orbit(sat_name, hours)
                    except ValueError:
                        print("❌ Invalid number of hours")
                        
            elif option == '7':
                # 3D visualization of Earth with satellites
                print("🌍 3D visualization of satellites around Earth")
                satellites_input = input("🛰️  Satellite names (comma separated): ").strip()
                if satellites_input:
                    satellite_names = [name.strip() for name in satellites_input.split(',')]
                    try:
                        hours = int(input("⏰ Trajectory hours (default 12): ") or "12")
                        print("⏳ Generating 3D visualization...")
                        analyzer.plot_3d_earth_with_satellites(satellite_names, hours)
                    except ValueError:
                        print("❌ Invalid number of hours")
                        
            elif option == '8':
                # 3D orbital animation
                sat_name = input("🎬 Satellite name to animate: ").strip()
                if sat_name:
                    try:
                        hours = int(input("⏰ Orbit hours to animate (default 6): ") or "6")
                        frames = int(input("🎞️  Number of frames (default 50): ") or "50")
                        print("⏳ Generating 3D animation...")
                        analyzer.plot_orbital_animation(sat_name, hours, frames)
                    except ValueError:
                        print("❌ Invalid values")
                        
            elif option == '8':
                print("👋 Thank you for using the Satellite Analysis System!")
                break
                
            else:
                print("❌ Invalid option. Select 1-16.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Program interrupted by user. See you later!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")


class RealisticOrbitPropagator:
    """
    Advanced orbital propagator with real physical perturbations
    Implements: J2, atmospheric drag, solar radiation pressure
    """
    
    def __init__(self):
        self.earth_radius = 6378.137  # km
        self.J2 = 1.08262668e-3      # J2 coefficient (Earth's oblateness)
        self.GM = 398600.4418        # km³/s² (Earth's gravitational constant)
        self.earth_rotation_rate = 7.2921159e-5  # rad/s
        
    def calculate_perturbations(self, satellite, t):
        """
        Calculate J2 perturbations (Earth's oblateness)
        J2 perturbation is the most significant for LEO orbits
        """
        try:
            # Get current position
            position = satellite.position.km
            r = np.linalg.norm(position)
            
            if r == 0:
                return np.array([0, 0, 0])
                
            # Normalized coordinates
            x, y, z = position / r
            
            # Geocentric latitude
            lat = np.arcsin(z)
            
            # J2 factor
            factor = -1.5 * self.J2 * (self.earth_radius**2 / r**4) * self.GM
            
            # J2 acceleration components
            accel_x = factor * x * (1 - 5 * z**2)
            accel_y = factor * y * (1 - 5 * z**2)
            accel_z = factor * z * (3 - 5 * z**2)
            
            return np.array([accel_x, accel_y, accel_z])
            
        except Exception as e:
            print(f"⚠️ Error calculating J2 perturbations: {e}")
            return np.array([0, 0, 0])
    
    def atmospheric_drag(self, satellite, t, solar_activity='moderate'):
        """
        Atmospheric drag (simplified MSIS-E00 model)
        Factors: atmospheric density, area/mass, drag coefficient
        """
        try:
            position = satellite.position.km
            r = np.linalg.norm(position)
            altitude = r - self.earth_radius
            
            # Only apply drag below 2000 km
            if altitude > 2000:
                return np.array([0, 0, 0])
            
            # Improved exponential atmospheric density model
            if altitude > 1000:
                # Exosphere
                scale_height = 268
                rho_0 = 3.019e-15  # kg/m³ at 1000 km
            elif altitude > 500:
                # Upper thermosphere
                scale_height = 60
                rho_0 = 2.418e-11  # kg/m³ at 500 km
            elif altitude > 200:
                # Lower thermosphere
                scale_height = 37
                rho_0 = 2.789e-11  # kg/m³ at 200 km
            else:
                # Mesosphere/Stratosphere
                scale_height = 22
                rho_0 = 3.899e-9   # kg/m³ at 200 km
            
            # Density with solar activity variation
            solar_factors = {
                'low': 0.7,
                'moderate': 1.0,
                'high': 1.5,
                'extreme': 2.2
            }
            
            solar_factor = solar_factors.get(solar_activity, 1.0)
            
            # Atmospheric density
            rho = rho_0 * solar_factor * np.exp(-(altitude - 200) / scale_height)
            
            # Relative velocity (considering Earth's rotation)
            velocity = satellite.velocity.km_per_s
            v_rel_mag = np.linalg.norm(velocity)
            
            if v_rel_mag == 0:
                return np.array([0, 0, 0])
            
            # Typical satellite parameters
            drag_coefficient = 2.2  # Typical drag coefficient
            area_to_mass = 0.01     # m²/kg (typical for small satellites)
            
            # Drag acceleration
            drag_magnitude = -0.5 * rho * drag_coefficient * area_to_mass * v_rel_mag**2
            drag_direction = velocity / v_rel_mag
            
            # Convert to km/s²
            drag_accel = drag_magnitude * drag_direction * 1e-3
            
            return drag_accel
            
        except Exception as e:
            print(f"⚠️ Error calculating atmospheric drag: {e}")
            return np.array([0, 0, 0])
    
    def solar_radiation_pressure(self, satellite, t):
        """
        Solar radiation pressure (significant for satellites with large panels)
        """
        try:
            # Solar constant at 1 AU
            solar_constant = 1361  # W/m²
            c = 299792458  # m/s speed of light
            
            # Radiation pressure
            radiation_pressure = solar_constant / c  # N/m²
            
            # Effective area (simplified - depends on orientation)
            effective_area = 10  # m² (estimate for typical satellite)
            
            # Reflectance factor (0 = total absorption, 1 = total reflection)
            reflectance_factor = 0.6
            
            # Only apply when satellite is illuminated by sun
            # (simplification: assume always illuminated)
            
            position = satellite.position.km
            r = np.linalg.norm(position)
            
            if r == 0:
                return np.array([0, 0, 0])
            
            # Direction from Earth's center to satellite
            direction = position / r
            
            # Typical satellite mass (kg)
            satellite_mass = 1000  # kg
            
            # Acceleration due to radiation pressure (very small)
            srp_magnitude = radiation_pressure * effective_area * (1 + reflectance_factor) / satellite_mass
            
            # Convert to km/s²
            srp_accel = srp_magnitude * direction * 1e-3
            
            return srp_accel
            
        except Exception as e:
            print(f"⚠️ Error calculating solar radiation pressure: {e}")
            return np.array([0, 0, 0])


class AdvancedCollisionAnalyzer:
    """
    Advanced collision analyzer with real statistical probability
    Implements uncertainty ellipsoids and covariance analysis
    """
    
    def __init__(self):
        self.min_distance_threshold = 5.0  # km
        self.high_risk_threshold = 1.0     # km
        
    def calculate_collision_probability(self, sat1_data, sat2_data, time_window_hours=24):
        """
        Calculate REAL collision probability using:
        - Uncertainty ellipsoids
        - Positional covariance
        - Physical satellite sizes
        """
        try:
            # Basic satellite data
            pos1 = np.array(sat1_data['position'])
            pos2 = np.array(sat2_data['position'])
            vel1 = np.array(sat1_data['velocity'])
            vel2 = np.array(sat2_data['velocity'])
            
            # Covariance matrices (6x6: position + velocity)
            # In reality, these come from tracking analysis
            covar1 = self._generate_covariance_matrix(sat1_data)
            covar2 = self._generate_covariance_matrix(sat2_data)
            
            # Combine covariance matrices
            P = covar1 + covar2
            
            # Relative state vector [Δx, Δy, Δz, Δvx, Δvy, Δvz]
            relative_state = np.concatenate([pos1 - pos2, vel1 - vel2])
            
            # Extract positional covariance (3x3)
            P_pos = P[:3, :3]
            
            # Normalized miss distance (Mahalanobis distance)
            try:
                P_pos_inv = np.linalg.inv(P_pos)
                miss_distance_normalized = np.sqrt(
                    relative_state[:3].T @ P_pos_inv @ relative_state[:3]
                )
            except np.linalg.LinAlgError:
                # If matrix is not invertible, use simplified method
                miss_distance_normalized = np.linalg.norm(relative_state[:3]) / np.sqrt(np.trace(P_pos))
            
            # Combined physical sizes
            radius1 = sat1_data.get('radius', 5.0)  # meters
            radius2 = sat2_data.get('radius', 5.0)  # meters
            combined_radius = (radius1 + radius2) / 1000  # convert to km
            
            # Probability calculation using complementary error function
            # This is an approximation of the probability integral
            sigma_miss = np.sqrt(np.trace(P_pos)) / 1000  # convert to km
            
            if sigma_miss > 0:
                # Probability based on multivariate normal distribution
                if SCIPY_AVAILABLE:
                    from scipy.special import erfc
                    prob_collision = 0.5 * erfc(
                        (miss_distance_normalized - combined_radius) / (sigma_miss * np.sqrt(2))
                    )
                else:
                    # Fallback: approximation using exponential function
                    # Not as accurate as erfc but works without SciPy
                    normalized_distance = (miss_distance_normalized - combined_radius) / (sigma_miss * np.sqrt(2))
                    # Approximation: erfc(x) ≈ exp(-x²) for x > 0
                    if normalized_distance > 0:
                        prob_collision = 0.5 * np.exp(-normalized_distance**2)
                    else:
                        prob_collision = 0.5  # Critical case
                
                # Limit probability between 0 and 1
                prob_collision = max(0, min(1, prob_collision))
            else:
                # Fallback: deterministic analysis
                actual_distance = np.linalg.norm(relative_state[:3])
                prob_collision = 1.0 if actual_distance < combined_radius else 0.0
            
            return {
                'probability': prob_collision,
                'miss_distance_km': np.linalg.norm(relative_state[:3]),
                'combined_radius_km': combined_radius,
                'uncertainty_ellipsoid': self._calculate_uncertainty_ellipsoid(P_pos),
                'risk_level': self._assess_risk_level(prob_collision, np.linalg.norm(relative_state[:3]))
            }
            
        except Exception as e:
            print(f"⚠️ Error calculating collision probability: {e}")
            return {
                'probability': 0.0,
                'miss_distance_km': float('inf'),
                'error': str(e)
            }
    
    def _generate_covariance_matrix(self, sat_data):
        """
        Generar matriz de covarianza 6x6 realista basada en el tipo de satélite
        """
        # Valores típicos de incertidumbre basados en capacidades de tracking
        position_std = {
            'LEO': [100, 50, 30],      # m [along-track, cross-track, radial]
            'MEO': [200, 100, 60],     # m
            'GEO': [500, 250, 150],    # m
            'HEO': [1000, 500, 300]   # m
        }
        
        velocity_std = {
            'LEO': [0.1, 0.05, 0.03],   # m/s
            'MEO': [0.2, 0.1, 0.06],    # m/s
            'GEO': [0.5, 0.25, 0.15],   # m/s
            'HEO': [1.0, 0.5, 0.3]      # m/s
        }
        
        # Determinar tipo de órbita basado en altitud
        altitude = sat_data.get('altitude', 500)
        if altitude < 2000:
            orbit_type = 'LEO'
        elif altitude < 20000:
            orbit_type = 'MEO'
        elif altitude < 50000:
            orbit_type = 'GEO'
        else:
            orbit_type = 'HEO'
        
        # Crear matriz de covarianza diagonal (simplificada)
        pos_std = position_std[orbit_type]
        vel_std = velocity_std[orbit_type]
        
        covariance = np.zeros((6, 6))
        
        # Covarianza posicional (convertir a km)
        for i in range(3):
            covariance[i, i] = (pos_std[i] / 1000) ** 2
        
        # Covarianza de velocidad (convertir a km/s)
        for i in range(3):
            covariance[i+3, i+3] = (vel_std[i] / 1000) ** 2
        
        # Agregar correlaciones cruzadas (simplificado)
        # En realidad, estas correlaciones son complejas y dependen de la geometría orbital
        correlation_factor = 0.1
        for i in range(3):
            covariance[i, i+3] = correlation_factor * np.sqrt(covariance[i, i] * covariance[i+3, i+3])
            covariance[i+3, i] = covariance[i, i+3]
        
        return covariance
    
    def _calculate_uncertainty_ellipsoid(self, P_pos):
        """
        Calcular parámetros del elipsoide de incertidumbre 3D
        """
        try:
            # Eigenvalores y eigenvectores de la matriz de covarianza
            eigenvalues, eigenvectors = np.linalg.eigh(P_pos)
            
            # Semi-ejes del elipsoide (3-sigma)
            semi_axes = 3 * np.sqrt(eigenvalues) * 1000  # convertir a metros
            
            return {
                'semi_axes_m': semi_axes,
                'orientation': eigenvectors,
                'volume_km3': (4/3) * np.pi * np.prod(semi_axes) / 1e9
            }
        except:
            return {'error': 'No se pudo calcular elipsoide de incertidumbre'}
    
    def _assess_risk_level(self, probability, distance_km):
        """Evaluar nivel de riesgo basado en probabilidad y distancia"""
        if probability > 1e-4 or distance_km < 1.0:
            return 'CRÍTICO'
        elif probability > 1e-6 or distance_km < 5.0:
            return 'ALTO'
        elif probability > 1e-8 or distance_km < 10.0:
            return 'MODERADO'
        else:
            return 'BAJO'


class UncertaintyModel:
    """
    Modelo avanzado de propagación de incertidumbre orbital
    """
    
    def __init__(self):
        self.base_uncertainty = {
            'along_track': 100,    # m (dirección del movimiento)
            'cross_track': 50,     # m (perpendicular al plano orbital)
            'radial': 30,          # m (hacia el centro de la Tierra)
        }
        
        # Tasas de crecimiento de incertidumbre (no lineales)
        self.growth_rates = {
            'along_track': 0.002,  # m/s (crece más rápido)
            'cross_track': 0.001,  # m/s
            'radial': 0.0005,      # m/s (crece más lento)
        }
        
        # Factores de acoplamiento (perturbaciones aumentan incertidumbre)
        self.coupling_factors = {
            'J2_coupling': 1.2,
            'drag_coupling': 1.5,
            'solar_pressure_coupling': 1.1
        }
    
    def propagate_uncertainty(self, time_hours, orbital_period_hours, perturbation_level='moderate'):
        """
        Propagar incertidumbre en el tiempo con modelo no-lineal
        
        En realidad esto requiere integrar las ecuaciones de Ricatti
        junto con las ecuaciones de movimiento
        """
        try:
            # Número de órbitas
            n_orbits = time_hours / orbital_period_hours
            
            # Factor de crecimiento no-lineal
            # La incertidumbre crece más rápido en órbitas excéntricas
            nonlinear_factor = 1 + 0.1 * n_orbits  # crecimiento cuadrático simplificado
            
            # Factor de perturbación
            perturbation_factors = {
                'low': 1.0,
                'moderate': 1.3,
                'high': 1.8,
                'extreme': 2.5
            }
            
            pert_factor = perturbation_factors.get(perturbation_level, 1.3)
            
            # Matriz de covarianza propagada (6x6)
            propagated_covariance = np.zeros((6, 6))
            
            # Incertidumbre posicional propagada
            for i, direction in enumerate(['along_track', 'cross_track', 'radial']):
                base_std = self.base_uncertainty[direction]
                growth_rate = self.growth_rates[direction]
                
                # Crecimiento cuadrático con el tiempo
                propagated_std = base_std + growth_rate * time_hours * 3600  # convertir a segundos
                propagated_std *= nonlinear_factor * pert_factor
                
                # Convertir a km y elevar al cuadrado para varianza
                propagated_covariance[i, i] = (propagated_std / 1000) ** 2
            
            # Incertidumbre de velocidad (derivada de la posicional)
            for i in range(3):
                # La incertidumbre de velocidad está relacionada con la posicional
                # dividida por el período orbital
                pos_std_km = np.sqrt(propagated_covariance[i, i])
                vel_std_km_s = pos_std_km / (orbital_period_hours * 3600)
                propagated_covariance[i+3, i+3] = vel_std_km_s ** 2
            
            # Correlaciones cruzadas (simplificadas)
            correlation_strength = min(0.3, 0.1 * n_orbits)  # aumenta con el tiempo
            
            for i in range(3):
                cross_correlation = correlation_strength * np.sqrt(
                    propagated_covariance[i, i] * propagated_covariance[i+3, i+3]
                )
                propagated_covariance[i, i+3] = cross_correlation
                propagated_covariance[i+3, i] = cross_correlation
            
            return {
                'covariance_matrix': propagated_covariance,
                'position_uncertainty_km': np.sqrt(np.diag(propagated_covariance[:3])),
                'velocity_uncertainty_km_s': np.sqrt(np.diag(propagated_covariance[3:])),
                'total_position_uncertainty_km': np.sqrt(np.trace(propagated_covariance[:3, :3])),
                'propagation_time_hours': time_hours,
                'orbits_completed': n_orbits
            }
            
        except Exception as e:
            print(f"⚠️ Error propagando incertidumbre: {e}")
            return {'error': str(e)}
    
    def calculate_maneuver_uncertainty(self, delta_v_m_s, execution_accuracy=0.1):
        """
        Calcular incertidumbre introducida por maniobras de evasión
        """
        try:
            # La ejecución de maniobras introduce incertidumbre adicional
            # debido a errores en el control de propulsión
            
            maneuver_uncertainty = {
                'delta_v_error': delta_v_m_s * execution_accuracy,  # error típico 10%
                'pointing_error_deg': 0.5,  # error de apuntamiento
                'timing_error_s': 1.0       # error de tiempo de ejecución
            }
            
            # Convertir a incertidumbre posicional después de la maniobra
            # (simplificación - en realidad requiere propagación completa)
            
            position_uncertainty_km = maneuver_uncertainty['delta_v_error'] * 0.1 / 1000  # regla empírica
            
            return {
                'maneuver_uncertainty': maneuver_uncertainty,
                'additional_position_uncertainty_km': position_uncertainty_km,
                'confidence_degradation': execution_accuracy
            }
            
        except Exception as e:
            print(f"⚠️ Error calculating maneuver uncertainty: {e}")
            return {'error': str(e)}


if __name__ == "__main__":
    main()
