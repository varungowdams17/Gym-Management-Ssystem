const mongoose = require('mongoose');
mongoose.connect('mongodb://127.0.0.1:27017/vehicle_service').then(async () => {
  try {
    const ServiceBooking = require('./backend/models/ServiceBooking');
    const Vehicle = require('./backend/models/Vehicle');
    const vehicles = await Vehicle.find({});
    console.log('Vehicles:', vehicles);
    const vehicleIds = vehicles.map(v => v._id);
    const bookings = await ServiceBooking.find({ vehicle_id: { $in: vehicleIds } })
      .populate('vehicle_id')
      .populate('service_type_id')
      .populate('center_id')
      .populate('mechanic_id');
    console.log('Bookings array size:', bookings.length);
    console.log('First booking stringified:', JSON.stringify(bookings[0], null, 2));
    
    // Test if some references are broken
    const invalidBookings = await ServiceBooking.find({ vehicle_id: { $in: vehicleIds } });
    console.log('Invalid bookings size (unpopulated):', invalidBookings.length);
    for (let b of bookings) {
      if (!b.vehicle_id || !b.service_type_id || !b.center_id) {
        console.log('Broken reference in booking:', b._id);
      }
    }

  } catch (err) {
    console.error(err);
  } finally {
    process.exit(0);
  }
});
