from settings import *

import pandas as pd
import numpy as np
import math

from scipy import signal



class Morphodynamics:
    def __init__(self):

        # Initialize v, r, and z
        self.rough = np.random.uniform(0, Rmax, (ROWS, COLS)) # random roughness surface

        # Add a subtle slope? Just forces more elongate deposits (preferential/directed path selection)
        x = np.linspace(COLS, 1, COLS)
        y = np.linspace(ROWS, 1, ROWS)
        _, self.yv = np.meshgrid(x, y)

        # Underlying topography domain (roughness and slope)
        self.z = self.rough + self.yv
        self.zo = self.z.copy()

        self.move = np.zeros((ROWS, COLS)) # tracks 'move' volume surface
        self.sand = np.zeros((ROWS, COLS)) # sediment volume surface

        # Initialise BERM & WATER LEVEL
        self.berm_o = np.zeros((1, COLS)) + H
        self.waterline_o = self.berm_o.copy() # water height – initially, same as berm

        self.berm = self.berm_o.copy()
        self.waterline = self.waterline_o.copy()

        # initialise flags
        self.inside_flag = 1 # starts ON (that is, ready to overwash when the timer goes...)

        self.lateral = 0
        self.temp_updated_throat_stack = np.zeros((1, COLS))
        self.store_sandy_subset = np.zeros((1, COLS))
        self.sandy_fill = np.zeros((1, COLS))



    # Function to generate random sand tiles
    def random_sand(self):
        for _ in range(50):
            x = np.random.randint(2, ROWS - 5) # keep random sand off the leading edge of the domain
            y = np.random.randint(0, COLS - 5)

            self.sand[x, y] = np.random.uniform(0, Vmin)
        
        self.z = self.zo + self.sand

    

    # Throat sites SET-UP ("directed random walk" approach)...
    def breach_sites(self):

        # Create random roughness surface
        r = np.random.uniform(0, 0.5, (ROWS_DRW, COLS)) # random roughness surface
        r[0, :] = 1 # Set all elements of the first row to 1

        # Create the "catchment flow" array of same size, but filled with zeros
        c = np.zeros_like(r)
        c = c.astype(int)
        c[0, :] = 1 # Set all elements of the first row to 1


        # Iterate through elements of 'r'
        for i in range(ROWS_DRW - 1):  # excluding the last row
            for j in range(COLS):
                
                if c[i, j] > 0:
                # Edge case: first element of the row
                    if j == 0:
                        neighbor_values = [r[i+1, j], r[i+1, j+1]]
                        min_neighbor_index = np.argmin(neighbor_values)
                        if min_neighbor_index == 0:
                            c[i+1, j] += c[i, j]
                        else:
                            c[i+1, j+1] += c[i, j]
                    # Edge case: last element of the row
                    elif j == COLS - 1:
                        neighbor_values = [r[i+1, j-1], r[i+1, j]]
                        min_neighbor_index = np.argmin(neighbor_values)
                        if min_neighbor_index == 0:
                            c[i+1, j-1] += c[i, j]
                        else:
                            c[i+1, j] += c[i, j]
                    # General case
                    else:
                        neighbor_values = [r[i+1, j-1], r[i+1, j], r[i+1, j+1]]
                        min_neighbor_index = np.argmin(neighbor_values)
                        if min_neighbor_index == 0:
                            c[i+1, j-1] += c[i, j]
                        elif min_neighbor_index == 1:
                            c[i+1, j] += c[i, j]
                        else:
                            c[i+1, j+1] += c[i, j]


        # Extract the last row of 'c'
        last_row = c[ROWS_DRW - 1, :]

        self.forcing_pattern = c.copy()

        self.capture = (last_row / np.sum(last_row))

        # Initialise overwash throats
        self.throat = np.zeros((1, COLS))
        self.throat += self.capture*H # this is the "full incision depth" to which the throats will evolve, absent manipulation

        # save this for 'breach_update' routine
        self.capture_array = self.capture.reshape(1, -1)

        nonz = np.nonzero(self.capture_array)[1]
        nonz = nonz.reshape(-1, 1)
        self.capture_o = self.capture_array[0, nonz]

        self.nonzero_indices = np.nonzero(self.capture_array)[1]
        self.nonzero_indices = self.nonzero_indices.reshape(-1, 1)

        # Record spacing between throats
        if len(self.nonzero_indices) > 1:
            self.spacing = np.diff(self.nonzero_indices.flatten(), axis=0)/COLS

        self.depth_checks = np.zeros((len(self.nonzero_indices), 16)) # lots of columns
        self.isolated_throats = np.zeros((len(self.nonzero_indices), COLS))



    def breach_update(self, inc):

        fill_checks = self.isolated_throats.copy() # Check ALL sites because this COULD turn on a dormant/dry throat by displacing capture into it

        sandy_parts = []
        gapwfill_parts = []
        gap_V = []
        gapwfill_v = []

        gapV_all = []
        gwfv_all = []

        for n in range(len(fill_checks)):

            gap = fill_checks[n, :].copy() # 'gap' is the isolated throat (one at a time)

            # Find indices where the column values are greater than 0
            indices = np.nonzero(gap)[0]
            indices = indices.reshape(-1, 1)
            
            if len(indices) > 0: # as long as there is a throat...

                self.sandy_subset = np.zeros((1, COLS))
                self.sandy_subset[0, indices] = self.sand[0, indices] - (Vmin*inc) # where is there sand in the top row, minus the max amount we'd expect to be there
                self.sandy_subset[self.sandy_subset < 0] = 0 # ensure no negatives (bc there may indeed be less sand than Vmin*inc)

                # Logic here: if sandy_subset exceeds Vmin, means whole site had to have been plowed...so add the Vmin*inc back in...
                # can't differentiate plowed from natural when volume < Vmin
                self.sandy_subset[self.sandy_subset < 0] += Vmin*inc

                # Gap smaller by 'extra' sand fill
                gap_with_fill = gap - self.sandy_subset
                gap_with_fill[gap_with_fill < 0] = 0

                # Volume of the "ideal" gap (sum of 1D shape):
                gap_V = gap.sum()
                # Volume of the partially filled gap (sum of 1D shape):
                gapwfill_v = gap_with_fill.sum()

                # Append sum_value to sandy_part
                sandy_parts.append(self.sandy_subset)
                gapwfill_parts.append(gap_with_fill)

                self.store_sandy_subset = np.vstack((self.store_sandy_subset, self.sandy_subset))
                
            else:
                gap_V = 1  # If no indices are found, set summed values to 1, because will ensure 'frac_filled' = 0
                gapwfill_v = 1
            
            # Save these as lists...
            gapV_all.append([gap_V])
            gwfv_all.append([gapwfill_v])


        # Convert sandy_part from list of lists to a numpy array
        gapV_all = np.array(gapV_all)
        gwfv_all = np.array(gwfv_all)

        # Convert lists of arrays to arrays
        sandy_parts = np.concatenate(sandy_parts, axis=0)
        gapwfill_parts = np.concatenate(gapwfill_parts, axis=0)

        self.frac_filled = 1-(gwfv_all/gapV_all) # fraction by which each throat has been reduced

        L_neighbour = np.roll(self.nonzero_indices, 1)
        L_neighbour[0] = 0 # because first element has no left neighbour

        R_neighbour = np.roll(self.nonzero_indices, -1)
        R_neighbour[-1] = 0 # because last element has no right neighbour

        L_dist = self.nonzero_indices - L_neighbour
        L_dist[0] = 0

        R_dist = np.roll(L_dist, -1)

        capture_frac = self.capture_array[0, self.nonzero_indices]

        T_dist = L_dist + R_dist
        cap_to_L = capture_frac*self.frac_filled*(1 - (L_dist/T_dist)) # more goes to closer of two neighbours; only redist's from active throats bc 'dry' have cap frac = 0
        cap_to_R = capture_frac*self.frac_filled*(1 - (R_dist/T_dist))

        cap_gain = (np.roll(cap_to_L, 1) + np.roll(cap_to_R, -1)) # rolls Qleft to the left, Qright to the right, adds them
        cap_lost = capture_frac*self.frac_filled 
        cap_net = cap_gain - cap_lost

        self.lateral = cap_gain.sum()

        self.capture_new = capture_frac + cap_net # this is where a 'dry' throat can end up with more capture...
        self.capture_new[self.capture_new < 0] = 0 # ensure no negatives
        self.capture_new = self.capture_new/self.capture_new.sum()

        self.new_cap_array = np.zeros((1, COLS))
        # self.new_cap_array[0, self.nonzero_indices.ravel()] = self.capture_new # makes list into an array...
        self.new_cap_array[0, self.nonzero_indices] = self.capture_new # makes list into an array...

        self.capture_array = self.new_cap_array.copy()

        self.deck = np.concatenate((self.nonzero_indices, capture_frac, self.frac_filled, cap_to_L, cap_to_R, cap_lost, cap_gain, cap_net, self.capture_new), axis=1)

        columns = ['nz_indices', 'capture_frac', 'frac_filled', 'cap_to_L', 'cap_to_R', 'cap_lost', 'cap_gain', 'cap_net', 'cap_new']
        
        self.deck = pd.DataFrame(self.deck, columns=columns)



    def couple(self, sand_array_in):

        self.sand = sand_array_in

        self.z = self.zo + self.sand


    def stuck_check(self):

        # Append current indices to the list
        self.past_indices.append(self.indices)

        # Keep only the last five sets of indices
        if len(self.past_indices) > 5:
            self.past_indices.pop(0)
            
        if len(self.past_indices) == 5:
            if np.array_equal(self.past_indices[0], self.past_indices[2]) and np.array_equal(self.past_indices[0], self.past_indices[4]):
                self.inside_flag = 0

        
    def overwash_conditions(self, perc, inc):

        # initialise indices...
        self.indices = []
        self.past_indices = []
        
        percent = perc/10

        # a bunch of variables that don't change during run, like L/R distances between breach sites – capture on the first iteration:
        if inc == 1:

            self.berm = self.berm_o.copy()
            self.waterline = self.waterline_o.copy()
            
            self.depth_checks[:, 2] = inc
            self.depth_checks[:, 3] = percent


            # collect the neighbours, distance to neighbors...[but do not need to do this every time, since they stay the same...same for check breaches]
            L_neighbour = np.roll(self.nonzero_indices, 1)
            L_neighbour[0] = 0 # because first element has no left neighbour

            R_neighbour = np.roll(self.nonzero_indices, -1)
            R_neighbour[-1] = 0 # because last element has no right neighbour

            L_dist = self.nonzero_indices - L_neighbour
            L_dist[0] = 0

            R_dist = np.roll(L_dist, -1)

            # store L/R distances in the big array – will need them for reapportioning
            self.depth_checks[:, 8] = L_dist.flatten()
            self.depth_checks[:, 9] = R_dist.flatten()


            self.depth_checks[:, 0] = self.nonzero_indices.flatten()

            site = 0
            for nz in self.nonzero_indices:

                # initial fractional depth of each throat at RDW site:
                self.isolated_throats[site, nz] = self.capture_array[0, nz]*H*self.depth_checks[site, 3]

                temp_inc = inc
                temp_perc = percent

                # make the throat shape for each throat in turn:
                temp_kernel = signal.windows.general_gaussian((1 + temp_inc), p = 1.5, sig = (2 + temp_perc))
                self.isolated_throats[site, :] = signal.convolve(self.isolated_throats[site, :], temp_kernel, mode='same')

                # update/populate the array
                self.depth_checks[site, 2] += 1 # increment site-specific inc
                self.depth_checks[site, 3] += 0.1 # increment site-specific perc

                self.depth_checks[site, 4] = 1 # set all throats to 'on'

                self.depth_checks[site, 5] = self.capture_array[0, nz] # original capture percentage
                self.depth_checks[site, 6] = 0 # capture percentage last used (important for reconstructing 'dry' throats)
                self.depth_checks[site, 7] = self.capture_array[0, nz] # this will be the 'new' capture percentage for comparison; match original in first iteration

                site += 1 # move to next row (next site in list)


        # Subsequent iterations:
        if inc > 1:

            # save previous throat at waterline before the routine really kicks off...
            self.throat_temp_previous = self.throat_temp.copy()
            self.waterline_previous = self.waterline.copy()

                    
            site = 0
            for nz in self.nonzero_indices:

                # calculate depth D of berm under waterline:
                D = self.waterline[0, nz] - self.berm[0, nz]

                self.depth_checks[site, 1] = D[0] # store D in big array

                # Check D (depth) threshold, switch on/off
                if D[0] > thresh: # if D > depth threshold, then site is active (water in the throat); otherwise 'off' (dry)
                    self.depth_checks[site, 4] = 1 # set to 'on'
                else:
                    self.depth_checks[site, 4] = 0 # set to 'off'

                # Load in current capture array:
                self.depth_checks[site, 7] = self.capture_array[0, nz] # this is the active/current capture array, which might include sites already zeroed out

                site += 1


            self.mask_on = self.depth_checks[:, 4] == 1 # select just the 'on' sites ('breach update' needs this one...)
            self.mask_off = self.depth_checks[:, 4] == 0 # select just the 'off' sites


            # If any of the sites are off, need to reapportion their capture
            if self.mask_off.sum() > 0:

                self.depth_checks[:, 10:] = 0 # clear the variable part of the big array so there are no vestigial addition/subtraction issues...

                for n in range(len(self.depth_checks)):

                    redistribute = self.depth_checks[n, 7] # amount of capture at that throat
                    
                    # redistribute the 'off' throat...
                    if self.depth_checks[n, 4] == 0 and redistribute > 0: # needs to be both OFF and not already been redistributed...

                        self.depth_checks[n, 6] = redistribute # log this "last used capture value" for reconstructing dry throats

                        # pull relative distances from the array...
                        L_distance = self.depth_checks[n, 8]
                        R_distance = self.depth_checks[n, 9]
                        tot_distance = L_distance + R_distance

                        capture_to_L = redistribute*(1 - (L_distance/tot_distance)) # more goes to closer of two neighbours
                        self.depth_checks[n, 10] = capture_to_L
                        capture_to_R = redistribute*(1 - (R_distance/tot_distance))
                        self.depth_checks[n, 11] = capture_to_R

                        cap_gain = (np.roll(self.depth_checks[:, 10], 1) + np.roll(self.depth_checks[:, 11], -1)) # rolls Qleft to the left, Qright to the right, adds them
                        self.depth_checks[:, 12] += cap_gain
                        self.depth_checks[n, 13] = redistribute

                # calc net capture – perform outside loop because there might be more than one site to redistribute (eg, two similarly shallow ones):
                self.depth_checks[:, 14] = self.depth_checks[:, 12] - self.depth_checks[:, 13] # net = gain - loss
                self.depth_checks[:, 15] = self.depth_checks[:, 7] + self.depth_checks[:, 14] # adjusted capture; these are the new capture values

                self.capture_new = self.depth_checks[:, 15] # assign as new capture values (list, not array)
                self.capture_new[self.capture_new < 0] = 0 # ensure no negatives
                self.capture_new = self.capture_new/self.capture_new.sum() # also ensure nothing greater than 100% – which can happen if a throat becomes reactivated

                # update capture ARRAY (from list)
                self.new_cap_array = np.zeros((1, COLS))
                self.new_cap_array[0, self.nonzero_indices.flatten()] = self.capture_new

                self.capture_array = self.new_cap_array.copy() # this is the new capture array


            # Now make the actual throats, update berm and waterline...
            # note that this zeroes out the isolated_throats array every iteration – none saved
            self.isolated_throats = np.zeros((len(self.nonzero_indices), COLS)) # need isolated throats for each site, combine at the end – initiate blanks


            for n in range(len(self.depth_checks)): # steps down each row in turn

                nz = int(self.depth_checks[n, 0]) # id element of the nonzero breach site

                D = self.depth_checks[n, 1] # pull depth at breach site

                temp_inc = self.depth_checks[n, 2] # pull last saved increment for that site (parameters to use this time to make throat)
                temp_perc = self.depth_checks[n, 3] # pull last saved percentage for that site
                

                if D > thresh:
                    # if D > thresh, then use the 'current' capture array
                    self.isolated_throats[n, nz] = self.capture_array[0, nz]*H*temp_perc

                    temp_kernel = signal.windows.general_gaussian((1 + temp_inc), p = 1.5, sig = (2 + temp_perc))
                    self.isolated_throats[n, :] = signal.convolve(self.isolated_throats[n, :], temp_kernel, mode='same')

                    self.depth_checks[n, 2] += 1 # update site-specific inc
                    self.depth_checks[n, 3] += 0.1 # update site-specific perc

                    self.depth_checks[n, 4] = 1 # ensure set to 'on'

                else: # that is, if D < thresh, then use the 'current' capture array

                    self.temp_cap_array = np.zeros((1, COLS))
                    self.temp_cap_array[0, nz] = self.depth_checks[n, 6] # fill temp capture array with last used capture before dry throat reallocated (= 0 cap)

                    self.isolated_throats[n, nz] = self.temp_cap_array[0, nz]*H*(temp_perc - 0.1) # undo incremental updates to a 'dry' throat shape

                    temp_kernel = signal.windows.general_gaussian((1 + (temp_inc - 1)), p = 1.5, sig = (2 + (temp_perc - 0.1))) # undo incremental updates to a 'dry' throat shape
                    self.isolated_throats[n, :] = signal.convolve(self.isolated_throats[n, :], temp_kernel, mode='same')

                    self.depth_checks[n, 4] = 0 # ensure set to 'off'

                    # this amount needs to be removed from Qmove calculation - need 'vstack' in case there are n > 1 dry throats...
                    self.dry_throat_V = np.vstack((self.dry_throat_V, self.isolated_throats[n, :].copy()))

            
            self.depth_checks[:, 7] = self.capture_new.flatten() # update "new cap column"


        # once each site has been checked, convovle for new temp berm
        temp_updated_throat = self.isolated_throats.max(axis = 0) # don't add them – just take the maximum value in each site alongshore
        temp_updated_throat = temp_updated_throat.reshape(1, COLS)

        self.temp_updated_throat_stack = np.vstack((self.temp_updated_throat_stack, temp_updated_throat))

        updated_throat = self.temp_updated_throat_stack.max(axis = 0)
        self.sandy_fill = self.store_sandy_subset.max(axis = 0)

        # self.throat_temp = updated_throat.copy() # includes the dry throat
        self.throat_temp = updated_throat.copy() - self.sandy_fill # includes the dry throat
        self.throat_temp[self.throat_temp < 0] = 0
        self.throat_temp[self.throat_temp > H] = H

        # Berm minus the current shape of throat(s)
        self.berm = self.berm_o - self.throat_temp
        self.berm[self.berm < 0] = 0

        # Adjust water height, given throat(s)...
        self.waterline = self.berm_o - self.throat_temp.sum()/COLS

        # Save and label the 'big array'...don't need to save all this once I know it works
        columns = ['0_nz', '1_D', '2_inc', '3_perc', '4_on_off', '5_orig_cap', '6_last_used_cap', '7_new_cap', '8_L_dist',
                       '9_R_dist', '10_cap_to_L', '11_cap_to_R', '12_cap_gain', '13_redist', '14_net', '15_new_caps']
        
        self.depths_check_deck = pd.DataFrame(self.depth_checks, columns=columns)



        # Now start to apportion sand from the berm to the floodplain:
        # First iteration, move all of throat_temp:
        if inc == 1:
                
            # Qmove = waterline - berm

            self.Qmove = self.throat_temp
            self.Qmove[self.Qmove < 0] = 0 # ensure no negative values

            # Qm and Qmove same at first – diverge later, when all we want is the part of the throat that has changed...
            self.Qm = self.Qmove.reshape(-1)
            self.Qm[self.Qm < 0] = 0
            self.Qm_tot = self.Qmove.sum()

            # add initial "bumps" to the top edge of 'move'
            self.move[0,:] += self.Qm

            self.dry_throat_V = np.zeros((1, COLS)) # need this here, zeroed out, until it becomes updated later
                
        else: # when inc > 1...

            self.Qmove_previous = self.Qmove.copy() # preserve Qmove from the previous iteration
        
            # toward volume of sed to distribute, starting with WHOLE VOL of active throats – so, delete any volume of 'dry' throats:
            self.Qmove = self.throat_temp - self.dry_throat_V.max(axis = 0)
            self.Qmove[self.Qmove < 0] = 0 # ensure no negative values
            
            # Qm is the new throat volume minus the previous one – leaves just the new bumps of sediment to move around
            self.Qm = self.Qmove.reshape(-1) - self.Qmove_previous.reshape(-1)
            self.Qm[self.Qm < 0] = 0 # ensure no negative values
            self.Qm_tot = np.append(self.Qm_tot, self.Qm.sum()) # store running total

            self.move[0,:] += self.Qm # add initial "bumps" to the top edge of 'move'
            self.move[self.move < 0] = 0 # ensure no negative values


        self.temp_move = self.move.copy()
        self.store_tmv = np.zeros((ROWS, COLS)) # tracks 'move' volume surface




    def overwash(self):
        # Run the sand distribution process:
        # as long as any given element of the 'move' surface exceeds the min threshold...

        self.temp_move_vis = np.zeros((ROWS, COLS)) # tracks 'move' volume surface

        if np.any(self.temp_move > Vmin):

            # Find indices where move > Vmin
            self.indices = np.argwhere(self.temp_move > Vmin)

            # Initialize an array to store neighbors info:
            neighbors = []
            # Define the neighbors (relative positions):
            neighbor_offsets = [(i, j) for i in range(-1, 2) for j in range(-1, 2) if (i != 0 or j != 0)]

            temp_plus = np.zeros((ROWS, COLS))
            temp_minus = np.zeros((ROWS, COLS))
            
                        
            # Iterate over the indices – so, for each tile...
            for idx in self.indices:
                i, j = idx
                
                if i < ROWS and j < COLS:

                    # Initialize an array to store neighbors info:
                    neighbors = []

                    Q = self.temp_move[i, j] - Vmin

                    for offset_i, offset_j in neighbor_offsets:
                        neighbor_i, neighbor_j = i + offset_i, j + offset_j

                        if 0 <= neighbor_i < ROWS and 0 <= neighbor_j < COLS:
                            neighbor_name = ""

                            if offset_i == -1:
                                neighbor_name += "U"
                            elif offset_i == 0:
                                neighbor_name += "C"
                            else:
                                neighbor_name += "L"

                            if offset_j == -1:
                                neighbor_name += "L"
                            elif offset_j == 0:
                                neighbor_name += "C"
                            else:
                                neighbor_name += "R"

                            # Calc total elevation difference between current cell and neighbors
                            diff = self.z[i, j] - self.z[neighbor_i, neighbor_j] # because z includes sand layer...

                            # Adjust for the diagonal neighbors:
                            if neighbor_name in ['UL', 'UR', 'LR', 'LL']:
                                adj_diff = diff * math.sqrt(2) / 2
                            else:
                                adj_diff = diff * 1

                            # Compile all the parts
                            neighbors.append([neighbor_i, neighbor_j, diff, adj_diff])

                            # >>>>>>>>>>> end if statement for setting up the neighbours array
                        # >>>>>>>>>>> end 'for' loop for neighbours array                 

                    # Back into the 'if inside the domain' rule...
                    # Convert results to a NumPy array
                    neighbors_array = np.array(neighbors)

                    # Check for negative values in the third column (index 2)
                    cull_negs = neighbors_array[:, 2] < 0

                    neighbors_array_negs = neighbors_array.copy()
                    neighbors_array_negs = neighbors_array_negs[cull_negs] # keeps any negative neighbours
                    
                    # Use boolean indexing to remove rows with negative values
                    neighbors_array = neighbors_array[~cull_negs]
                    
                    if neighbors_array.size > 0:
                    
                        # Calculate Q_prop
                        Q_prop = Q * neighbors_array[:, 3] / neighbors_array[:, 3].sum()

                        temp_minus[i, j] -= Q # remove quantity Q from element in 'move'

                        # Append Q_prop as a new column to neighbors_array
                        neighbors_array = np.column_stack((neighbors_array, Q_prop))

                        # Loop through the rows of neighbors_array
                        for n in range(neighbors_array.shape[0]):
                            neighbor_i, neighbor_j = neighbors_array[n, 0:2].astype(int)

                            # update temp_plus surface
                            temp_plus[neighbor_i, neighbor_j] += neighbors_array[n, -1]  # Add Q_prop from neighbors_array

                    else:

                        neighbors_array_negs = abs(neighbors_array_negs)
                        
                        # bc negative values, need to flip around to make sure the most flux goes to the least negative neighbour
                        neighbors_array_negs[:, 3] = neighbors_array_negs[:, 3].max() - neighbors_array_negs[:, 3]

                        # Calculate Q_prop
                        Q_prop = Q * neighbors_array_negs[:, 3] / neighbors_array_negs[:, 3].sum()

                        temp_minus[i, j] -= Q # remove quantity Q from element in 'move'

                        # Append Q_prop as a new column to neighbors_array
                        neighbors_array_negs = np.column_stack((neighbors_array_negs, Q_prop))

                        # Loop through the rows of neighbors_array
                        for n in range(neighbors_array_negs.shape[0]):
                            neighbor_i, neighbor_j = neighbors_array_negs[n, 0:2].astype(int)

                            # update temp_plus surface
                            temp_plus[neighbor_i, neighbor_j] += neighbors_array_negs[n, -1]  # Add Q_prop from neighbors_array
                    

                    del neighbors_array
                    del neighbors_array_negs

                    # >>>>>>>>>>> end for loop through neighbours array (element scale)
                    
                # >>>>>>>>>>> end 'if i < ROWS and j <= COLS' condition (element scale)
                
            # >>>>>>>>>>> end of the the 'for idx in indices' condition...(list of active elements scale)

            self.temp_move += temp_plus + temp_minus

            self.temp_move_vis = self.temp_move.copy() # only for visuals...

            self.store_tmv += self.temp_move_vis
            
        # end of 'IF TRUE' condition  
        else: # that is, if np.any(self.move > Vmin) is not TRUE
            self.inside_flag = 0
                

                
    def make_washover(self):

        self.move = self.temp_move.copy()

        # Save total wet surface:
        self.wet = np.count_nonzero(self.move)

        self.move_to_sand = self.move.copy()
        self.move_to_sand[self.move_to_sand > Vmin] = Vmin
        
        self.sand += self.move_to_sand
            
        self.z = self.zo + self.sand
        
        self.move = self.move - Vmin
        self.move[self.move < 0] = 0
    

    def update(self, inc):

        self.stuck_check() # stuck?

        if self.inside_flag == 1: # if not stuck...run overwash
            self.breach_update(inc)
            self.overwash()