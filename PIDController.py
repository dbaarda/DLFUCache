#!/usr/bin/python3

def limit(value, minValue, maxValue):
  # limit a value between min and max
  return min(max(minValue, value), maxValue)


class PIDController(object):
  """A PID Controller.

  This is a PID controller with the following special features;

  * It uses "standard form" for easier interpretation of I and D terms.
  * The update interval dt can be variable and is provided per input.
  * The output is range limited for predictable output.
  * The integrator is range limited and preloaded based on the output range
    to avoid integrator windup.
  * There is a lowpass filter on the error input to reduce setpoint steps
    and/or feedback noise.
  * There is a lowpass filter on the derivative to avoid derivative noise
    spikes.
  * The derivative low-pass filter means this works for step inputs with
    dt=0.0.

  Note that variable sample rates have their own special complications, and
  it would be wise to try to keep the sample intervals short and regular.

  Attributes:
    Kp: The PID proportional gain.
    Ki: The PID integral gain.
    Kd: The PID derivative gain.
    Ld: The derivative lowpass filter timeconstant.
    Le: The error lowpass filter timeconstant.
    error: The last Kp scaled error.
    integ: The last Ki scaled integral.
    deriv: The last Kd scaled derivative.
    output: The control output.
  """

  outputMin = -1.0
  outputMax = 1.0
  integMin = outputMin - 1.0 * (outputMax - outputMin)
  integMax = outputMax + 1.0 * (outputMax - outputMin)

  def __init__(self, Kp, Ki, Kd, Ld=0.0, Le=0.0):
    self.Kp = Kp
    self.Ki = Ki
    self.Kd = Kd
    self.Ld = Ld
    self.Le = Le
    self.error = 0.0
    self.integ = (self.outputMin + self.outputMax) / 2.0
    self.deriv = 0.0
    self.output = self.integ

  @classmethod
  def StandardForm(cls, Kp, Ti, Td, Ld=None, Le=None):
    """Standard form PIDController initializer.

    This initialization uses the times over which the T and D terms
    effectively operate. Ti is how long in the past I term looks, and
    Td is how far in the future the D term looks. If Ld is None it
    will default to Td/8. If Le is None it defaults to Ld/8.

    Args:
      Kp: The PID proportional gain.
      Ti: The PID integral time.
      Td: The PID derivative time.
      Ld: The derivative lowpass filter timeconstant (default: Td/8)
      Le: The error lowpass filter timeconstant (default: Ld/8)

    Returns:
      An initialized PIDController.
    """
    if Ld is None:
      Ld = Td / 8.0
    if Le is None:
      Le = Ld / 8.0
    return cls(Kp, 1.0/Ti, Td, Ld, Le)

  @classmethod
  def ZiglerNichols(cls, Ku, Tu, Ld=None, Le=None):
    """ZiglerNichols PIDController initializer.

    This initialization uses the Classic PID Zeigler-Nichols tuning
    method based on a Ku ultimate gain and Tu oscillation period which
    are found by setting Ki=Kd=0.0 and increasing Kp until the system
    oscillates.

    Args:
      Ku: The PID ultimate gain.
      Tu: The PID ultimate oscillation period.
      Ld: The derivative low-pass filter RC time.

    Returns:
      An initialized PIDController.
    """
    return cls.StandardForm(0.6*Ku, Tu/2.0, Tu/8.0, Ld, Le)

  def update(self, error, dt=1.0):
    """Update with a new input.

    This is used to update with a new input and get the output.

    Args:
      error: input of demand - output.
      dt: time since last iteration.

    Returns:
      The control output.
    """
    # Calculate proportional term and lowpass filter if needed.
    error = self.Kp * error
    if self.Le:
      error = (dt * error + self.Le * self.error) / (dt + self.Le)
    # Accumulate trapezoidal integral of error scaled by Ki.
    integ = self.Ki * dt * (error + self.error) / 2.0 + self.integ
    # Limit integral term between integMin and integMax.
    integ = limit(integ, self.integMin, self.integMax)
    # Calculate linear derivative of error scaled by Kd and low-pass filter.
    # This is equivalent to the following except avoids divide by zero errors
    # when Ld>0.0 for dt=0.0;
    #   deriv = self.Kd * (error - self.error) / dt
    #   alpha = dt / (dt + self.Ld)
    #   deriv = alpha * deriv + (1.0 - alpha) * self.deriv
    deriv = (self.Kd * (error - self.error) + self.Ld * self.deriv) / (dt + self.Ld)
    # Calculate and limit output between outputMin and outputMax.
    self.output = limit(error + integ + deriv, self.outputMin, self.outputMax)
    # Save state variables.
    self.error = error
    self.integ = integ
    self.deriv = deriv
    return self.output

  def reset(self, error, dt=0.0):
    """Reset previous error to the provided value then update.

    This is used for preventing derivative term spikes for step
    changes in the demand.

    Args:
      error: input of demand - output.
      dt: time since last iteration.

    Returns:
      The control output.
    """
    self.error = self.Kp * error
    return self.update(error, dt)

  def __repr__(self):
    return "PIDController(Kp=%5.3f, Ki=%5.3f, Kd=%5.3f, Ld=%5.3f, Le=%5.3f)" % (
        self.Kp, self.Ki, self.Kd, self.Ld, self.Le)

  def __str__(self):
    return "%r: error=%+6.3f integ=%+6.3f deriv=%+6.3f output=%+6.3f" % (
        self, self.error, self.integ, self.deriv, self.output)


class LowPassFilter(object):

  def __init__(self, T, output=0.0):
    self.T = T
    self.output = output

  def update(self, value, dt=1.0):
    self.output = (value*dt + self.output*self.T) / (self.T + dt)
    return self.output

  def __repr__(self):
    return "LowPassFilter(T=%5.3f)" % self.T

  def __str__(self):
    return "%r: output=%+6.3f" % (self, self.output)


class LowPassFilter2(object):
  "A lowpass filter with different timeconstants for rising and falling."""

  def __init__(self, Tup, Tdn, output=0.0):
    self.Tup = Tup
    self.Tdn = Tdn
    self.output = output

  def update(self, value, dt=1.0):
    if value > self.output:
      T = self.Tup
    else:
      T = self.Tdn
    self.output = (value*dt + self.output*T) / (T + dt)
    return self.output

  def __repr__(self):
    return "LowPassFilter2(Tup=%5.3f, Tdn=%5.3f)" % (self.Tup, self.Tdn)

  def __str__(self):
    return "%r: output=%+6.3f" % (self, self.output)


if __name__ == '__main__':
  controller = PIDController.ZiglerNichols(Ku=5.0, Tu=15.0)
  demand = 1.0
  force = 0.0
  mass = 10.0
  position = 0.0
  velocity = 0.0
  print("%2d %6.3f %s" % (0, position, controller))
  controller.reset(demand - position)
  print("%2d %6.3f %s" % (0, position, controller))
  for t in range(40):
    velocity += force/mass
    position += velocity
    force = controller.update(demand - position, 1.0)
    print("%2d %6.3f %s" % (t, position, controller))
